import urllib
import string

import discord
import youtube_dl
from bs4 import BeautifulSoup

from config.config import *
from musicbot.playlist import Playlist
from musicbot.songinfo import Songinfo


def playing_string(title):
    filter(lambda x: x in set(string.printable), title)
    title_parts = title.split(" ")
    short_title = ""

    if len(title_parts) == 1:
        short_title = title[0:29]
    else:
        for part in title_parts:
            if len(short_title + part) > 28:
                break
            if short_title != "":
                short_title += " "
            short_title += part

    return "[" + short_title.replace("(", "|") + "]"


class AudioController:

    def __init__(self, bot, guild, volume):
        self.bot = bot
        self._volume = volume
        self.playlist = Playlist()
        self.current_songinfo = Songinfo()
        self.guild = guild

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = value
        try:
            self.guild.voice_client.source.volume = float(value) / 100.0
        except:
            pass

    def next_song(self, error):
        next_song = self.playlist.next()

        if next_song is None:
            coro = self.guild.me.edit(nick=DEFAULT_NICKNAME)
        else:
            coro = self.play_youtube(next_song)

        self.bot.loop.create_task(coro)

    async def add_song(self, track):
        if not ("watch?v=" in track):
            link = self.convert_to_youtube_link('"'+track+'"')
        if link is None:
            link = self.convert_to_youtube_link(track)
        if link is None:
            return
        self.playlist.add(link)
        if len(self.playlist.playque) == 1:
            await self.play_youtube(link)

    def convert_to_youtube_link(self, title):

        filter(lambda x: x in set(string.printable), title)

        query = urllib.parse.quote(title)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urllib.request.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html, "html.parser")
        results = soup.findAll(attrs={'class': 'yt-uix-tile-link'})
        if len(results) != 0:
            return 'https://www.youtube.com' + results[0]['href']
        else:
            return None

    async def play_youtube(self, youtube_link):
        try:
            downloader = youtube_dl.YoutubeDL({'format': 'bestaudio', 'title': True})
            extracted_info = downloader.extract_info(youtube_link, download=False)
        except:
            try:
                downloader = youtube_dl.YoutubeDL({})
                extracted_info = downloader.extract_info(youtube_link, download=False)
            except:
                self.next_song(None)


        await self.guild.me.edit(nick=playing_string(extracted_info.get('title')))
        self.guild.voice_client.play(discord.FFmpegPCMAudio(extracted_info['url']), after=lambda e: self.next_song(e))
        self.guild.voice_client.source = discord.PCMVolumeTransformer(self.guild.voice_client.source)
        self.guild.voice_client.source.volume = float(self.volume) / 100.0

    async def stop_player(self):
        if self.guild.voice_client is None or (
                not self.guild.voice_client.is_paused() and not self.guild.voice_client.is_playing()):
            return
        self.playlist.next()
        self.playlist.playque.clear()
        self.guild.voice_client.stop()
        await self.guild.me.edit(nick=DEFAULT_NICKNAME)

    async def prev_song(self):
        if len(self.playlist.playhistory) == 0:
            return None
        if self.guild.voice_client is None or (
                not self.guild.voice_client.is_paused() and not self.guild.voice_client.is_playing()):
            prev_song = self.playlist.prev()
            if prev_song == "Dummy":
                self.playlist.next()
                return None
            await self.play_youtube(prev_song)
        else:
            self.playlist.prev()
            self.playlist.prev()
            self.guild.voice_client.stop()