import json
import os
import sys
from pathlib import Path

import requests


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Canal oficial da Canção Nova
CHANNEL_ID = "UC6V9mqiVuzd-v3ozUfCtZFA"

ARQUIVO_ULTIMA_LIVE = Path("ultima_live.txt")


def fazer_requisicao(url: str, params: dict) -> dict:
    resposta = requests.get(url, params=params, timeout=30)
    resposta.raise_for_status()
    return resposta.json()


def obter_playlist_de_uploads() -> str:
    dados = fazer_requisicao(
        "https://www.googleapis.com/youtube/v3/channels",
        {
            "part": "contentDetails",
            "id": CHANNEL_ID,
            "key": YOUTUBE_API_KEY,
        },
    )

    itens = dados.get("items", [])

    if not itens:
        raise RuntimeError("Canal da Canção Nova não encontrado.")

    return itens[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def obter_videos_recentes(playlist_id: str) -> list[str]:
    dados = fazer_requisicao(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 10,
            "key": YOUTUBE_API_KEY,
        },
    )

    return [
        item["contentDetails"]["videoId"]
        for item in dados.get("items", [])
        if item.get("contentDetails", {}).get("videoId")
    ]


def encontrar_live_ativa(video_ids: list[str]) -> dict | None:
    if not video_ids:
        return None

    dados = fazer_requisicao(
        "https://www.googleapis.com/youtube/v3/videos",
        {
            "part": "snippet,liveStreamingDetails",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY,
        },
    )

    for video in dados.get("items", []):
        snippet = video.get("snippet", {})
        detalhes = video.get("liveStreamingDetails", {})

        esta_ao_vivo = snippet.get("liveBroadcastContent") == "live"
        iniciou = detalhes.get("actualStartTime")
        terminou = detalhes.get("actualEndTime")

        if esta_ao_vivo and iniciou and not terminou:
            return {
                "id": video["id"],
                "titulo": snippet.get("title", "Canção Nova ao vivo"),
                "thumbnail": (
                    snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url")
                ),
            }

    return None


def ler_ultima_live() -> str:
    if not ARQUIVO_ULTIMA_LIVE.exists():
        return ""

    return ARQUIVO_ULTIMA_LIVE.read_text(encoding="utf-8").strip()


def salvar_ultima_live(video_id: str) -> None:
    ARQUIVO_ULTIMA_LIVE.write_text(video_id, encoding="utf-8")


def enviar_para_discord(live: dict) -> None:
    link = f"https://www.youtube.com/watch?v={live['id']}"

    embed = {
        "title": "🔴 Canção Nova está AO VIVO!",
        "description": (
            f"🎥 **{live['titulo']}**\n\n"
            f"📺 **[Clique aqui para assistir à transmissão]({link})**\n\n"
            "🙏 Que Deus abençoe este momento de oração!"
        ),
        "url": link,
        "color": 15158332,
        "footer": {
            "text": "Canção Nova • Aviso de transmissão ao vivo"
        },
    }

    if live.get("thumbnail"):
        embed["image"] = {"url": live["thumbnail"]}

    resposta = requests.post(
        DISCORD_WEBHOOK,
        json={
            "username": "Canção Nova Ao Vivo",
            "content": "🔔 **A Canção Nova iniciou uma transmissão!**",
            "embeds": [embed],
        },
        timeout=30,
    )

    resposta.raise_for_status()


def main() -> None:
    if not YOUTUBE_API_KEY:
        print("❌ Secret YOUTUBE_API_KEY não configurado.")
        sys.exit(1)

    if not DISCORD_WEBHOOK:
        print("❌ Secret DISCORD_WEBHOOK não configurado.")
        sys.exit(1)

    playlist_id = obter_playlist_de_uploads()
    videos_recentes = obter_videos_recentes(playlist_id)
    live = encontrar_live_ativa(videos_recentes)

    if not live:
        print("⚪ A Canção Nova não está ao vivo neste momento.")
        return

    ultima_live = ler_ultima_live()

    if ultima_live == live["id"]:
        print(f"🟡 A live {live['id']} já foi avisada anteriormente.")
        return

    enviar_para_discord(live)
    salvar_ultima_live(live["id"])

    print(f"✅ Aviso enviado: {live['titulo']}")
    print(f"🔗 https://www.youtube.com/watch?v={live['id']}")


if __name__ == "__main__":
    main()
