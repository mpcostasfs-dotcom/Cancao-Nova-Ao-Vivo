import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

CHANNEL_ID = "UC6V9mqiVuzd-v3ozUfCtZFA"

ARQUIVO_ULTIMA_LIVE = Path("ultima_live.txt")
FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")


def fazer_requisicao(url: str, params: dict) -> dict:
    resposta = requests.get(url, params=params, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def buscar_live():
    dados = fazer_requisicao(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "channelId": CHANNEL_ID,
            "eventType": "live",
            "type": "video",
            "maxResults": 1,
            "key": YOUTUBE_API_KEY,
        },
    )

    itens = dados.get("items", [])

    if not itens:
        return None

    video_id = itens[0]["id"]["videoId"]

    dados_video = fazer_requisicao(
        "https://www.googleapis.com/youtube/v3/videos",
        {
            "part": "snippet,liveStreamingDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        },
    )

    video = dados_video["items"][0]

    snippet = video["snippet"]
    detalhes = video.get("liveStreamingDetails", {})

    thumbs = snippet.get("thumbnails", {})

    thumbnail = (
        thumbs.get("maxres", {}).get("url")
        or thumbs.get("standard", {}).get("url")
        or thumbs.get("high", {}).get("url")
        or thumbs.get("medium", {}).get("url")
        or thumbs.get("default", {}).get("url")
    )

    inicio = detalhes.get("actualStartTime")

    if inicio:
        inicio = (
            datetime.fromisoformat(inicio.replace("Z", "+00:00"))
            .astimezone(FUSO_BRASIL)
            .strftime("%d/%m/%Y às %H:%M")
        )

    espectadores = detalhes.get("concurrentViewers")

    if espectadores:
        espectadores = f"{int(espectadores):,}".replace(",", ".")

    return {
        "id": video_id,
        "titulo": snippet["title"],
        "thumbnail": thumbnail,
        "inicio": inicio,
        "espectadores": espectadores,
    }


def buscar_video_recente():
    dados = fazer_requisicao(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "channelId": CHANNEL_ID,
            "order": "date",
            "type": "video",
            "maxResults": 1,
            "key": YOUTUBE_API_KEY,
        },
    )

    itens = dados.get("items", [])

    if not itens:
        return None

    item = itens[0]

    snippet = item["snippet"]

    thumbs = snippet.get("thumbnails", {})

    thumbnail = (
        thumbs.get("maxres", {}).get("url")
        or thumbs.get("standard", {}).get("url")
        or thumbs.get("high", {}).get("url")
        or thumbs.get("medium", {}).get("url")
        or thumbs.get("default", {}).get("url")
    )

    return {
        "id": item["id"]["videoId"],
        "titulo": snippet["title"],
        "thumbnail": thumbnail,
        "publicado": snippet["publishedAt"],
    }


def ler_ultima_live():
    if not ARQUIVO_ULTIMA_LIVE.exists():
        return ""

    return ARQUIVO_ULTIMA_LIVE.read_text().strip()


def salvar_ultima_live(video_id):
    ARQUIVO_ULTIMA_LIVE.write_text(video_id)


def ler_ultimo_video():
    caminho = Path("ultimo_video.txt")

    if not caminho.exists():
        return ""

    return caminho.read_text().strip()


def salvar_ultimo_video(video_id):
    caminho = Path("ultimo_video.txt")
    caminho.write_text(video_id)


def enviar_para_discord(live):
    link = f"https://www.youtube.com/watch?v={live['id']}"

    campos = []

    if live.get("inicio"):
        campos.append(
            {
                "name": "🕐 Início da transmissão",
                "value": live["inicio"],
                "inline": True,
            }
        )

    if live.get("espectadores"):
        campos.append(
            {
                "name": "👥 Assistindo agora",
                "value": live["espectadores"],
                "inline": True,
            }
        )

    embed = {
        "title": "🔴 Canção Nova está AO VIVO!",
        "description": (
            f"## {live['titulo']}\n\n"
            f"📺 **[Clique aqui para assistir à transmissão]({link})**\n\n"
            "🙏 Que Deus abençoe este momento de fé e oração!"
        ),
        "url": link,
        "color": 15158332,
        "fields": campos,
        "footer": {
            "text": "Canção Nova • Transmissão ao vivo"
        },
    }

    if live.get("thumbnail"):
        embed["image"] = {
            "url": live["thumbnail"]
        }

    resposta = requests.post(
        DISCORD_WEBHOOK,
        json={
            "username": "📺 TV Canção Nova",
            "avatar_url": "https://raw.githubusercontent.com/mpcostasfs-dotcom/Cancao-Nova-Ao-Vivo/main/ChatGPT%20Image%2030%20de%20jul.%20de%202026%2C%2013_38_30.png",
            "content": "🔔 **A Canção Nova iniciou uma transmissão ao vivo!**",
            "embeds": [embed],
        },
        timeout=30,
    )

    resposta.raise_for_status()


def enviar_video_para_discord(video):
    link = f"https://www.youtube.com/watch?v={video['id']}"

    embed = {
        "title": "🎥 Novo vídeo publicado!",
        "description": (
            f"## {video['titulo']}\n\n"
            f"▶️ **[Clique aqui para assistir]({link})**"
        ),
        "url": link,
        "color": 3447003,
        "footer": {
            "text": "Canção Nova • Novo vídeo"
        },
    }

    if video.get("thumbnail"):
        embed["image"] = {
            "url": video["thumbnail"]
        }

    resposta = requests.post(
        DISCORD_WEBHOOK,
        json={
            "username": "📺 TV Canção Nova",
            "avatar_url": "https://raw.githubusercontent.com/mpcostasfs-dotcom/Cancao-Nova-Ao-Vivo/main/ChatGPT%20Image%2030%20de%20jul.%20de%202026%2C%2013_38_30.png",
            "content": "📢 **A Canção Nova publicou um novo vídeo!**",
            "embeds": [embed],
        },
        timeout=30,
    )

    resposta.raise_for_status()


def main():
    if not YOUTUBE_API_KEY:
        print("❌ Secret YOUTUBE_API_KEY não configurado.")
        sys.exit(1)

    if not DISCORD_WEBHOOK:
        print("❌ Secret DISCORD_WEBHOOK não configurado.")
        sys.exit(1)

    try:
        print("====================================")
        print("🔎 Verificando Canção Nova...")
        print("====================================")

        # -------------------------
        # VERIFICAR LIVE
        # -------------------------
        live = buscar_live()

        if live:
            print(f"🔴 Live encontrada: {live['titulo']}")

            ultima_live = ler_ultima_live()

            if ultima_live != live["id"]:
                enviar_para_discord(live)
                salvar_ultima_live(live["id"])
                print("✅ Nova live enviada ao Discord.")
            else:
                print("🟡 Live já avisada anteriormente.")
        else:
            print("⚪ Nenhuma live encontrada.")

        # -------------------------
        # VERIFICAR VÍDEO
        # -------------------------
        video = buscar_video_recente()

        if video:
            print(f"🎥 Último vídeo: {video['titulo']}")

            ultimo_video = ler_ultimo_video()

            if ultimo_video != video["id"]:
                enviar_video_para_discord(video)
                salvar_ultimo_video(video["id"])
                print("✅ Novo vídeo enviado ao Discord.")
            else:
                print("🟡 Último vídeo já foi avisado.")
        else:
            print("⚪ Nenhum vídeo encontrado.")

    except requests.RequestException as erro:
        print(f"❌ Erro de conexão: {erro}")
        sys.exit(1)

    except Exception as erro:
        print(f"❌ Erro: {erro}")
        sys.exit(1)


if __name__ == "__main__":
    main()
