# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# streamondemand 5
# Copyright 2015 tvalacarta@gmail.com
# http://www.mimediacenter.info/foro/viewforum.php?f=36
#
# Distributed under the terms of GNU General Public License v3 (GPLv3)
# http://www.gnu.org/licenses/gpl-3.0.html
# ------------------------------------------------------------
# This file is part of streamondemand 5.
#
# streamondemand 5 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# streamondemand 5 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with streamondemand 5.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------------------
# Search trailers from youtube, filmaffinity, abandomoviez, vimeo, etc...
# --------------------------------------------------------------------------------

import re
import urllib
import urlparse

from core import config
from core import jsontools
from core import logger
from core import scrapertools
from core import servertools
from core.item import Item
from platformcode import platformtools

result = None
window_select = []
DEBUG = config.get_setting("debug")
# Para habilitar o no la opción de búsqueda manual
if config.get_platform() != "plex":
    keyboard = True
else:
    keyboard = False


def buscartrailer(item, trailers=[]):
    logger.info("streamondemand.channels.trailertools buscartrailer")

    # Lista de acciones si se ejecuta desde el menú contextual
    if item.action == "manual_search" and item.contextual:
        itemlist = manual_search(item)
        item.contentTitle = itemlist[0].contentTitle
    elif 'search' in item.action and item.contextual:
        itemlist = globals()[item.action](item)
    else:
        # Se elimina la opción de Buscar Trailer del menú contextual para evitar redundancias
        if type(item.context) is str and "buscar_trailer" in item.context:
            item.context = item.context.replace("buscar_trailer", "")
        elif type(item.context) is list and "buscar_trailer" in item.context:
            item.context.remove("buscar_trailer")

        item.text_color = ""

        itemlist = []
        if item.contentTitle != "":
            item.contentTitle = item.contentTitle.strip()
        elif keyboard:
            fulltitle = re.sub('\[\/*(B|I|COLOR)\s*[^\]]*\]', '', item.fulltitle.strip())
            item.contentTitle = platformtools.dialog_input(default=fulltitle, heading="Introduce el título a buscar")
            if item.contentTitle is None:
                item.contentTitle = fulltitle
            else:
                item.contentTitle = item.contentTitle.strip()
        else:
            fulltitle = re.sub('\[\/*(B|I|COLOR)\s*[^\]]*\]', '', item.fulltitle.strip())
            item.contentTitle = fulltitle
        
        item.year = item.infoLabels['year']

        logger.info("streamondemand.channels.trailertools Búsqueda: %s" % item.contentTitle)
        logger.info("streamondemand.channels.trailertools Año: %s" % item.year)
        if item.infoLabels['trailer'] and not trailers:
            url = item.infoLabels['trailer']
            if "youtube" in url:
                url = url.replace("embed/", "watch?v=")
            titulo, url, server = servertools.findvideos(url)[0]
            title = "Trailer por defecto  [" + server + "]"
            itemlist.append(item.clone(title=title, url=url, server=server, action="play"))
        if item.show or item.infoLabels['tvshowtitle'] or item.contentType != "movie":
            tipo = "tv"
        else:
            tipo = "movie"
        try:
            if not trailers:
                itemlist.extend(tmdb_trailers(item, tipo))
            else:
                for trailer in trailers:
                    title = trailer['name'] + " [" + trailer['size'] + "p] (" + trailer['language'].replace("en", "ING")\
                            .replace("es", "ESP")+")  [tmdb/youtube]"
                    itemlist.append(item.clone(action="play", title=title, url=trailer['url'], server="youtube"))
        except:
            import traceback
            logger.error(traceback.format_exc())
        
        if item.contextual:
            title = "[COLOR green]%s[/COLOR]"
        else:
            title = "%s"
        itemlist.append(item.clone(title=title % "Búsqueda en Youtube", action="youtube_search",
                                   text_color="green"))
        itemlist.append(item.clone(title=title % "Búsqueda en Filmaffinity",
                                   action="filmaffinity_search", text_color="green"))
        # Si se trata de una serie, no se incluye la opción de buscar en Abandomoviez
        if not item.show and not item.infoLabels['tvshowtitle']:
            itemlist.append(item.clone(title=title % "Búsqueda en Abandomoviez",
                                       action="abandomoviez_search", text_color="green"))
        itemlist.append(item.clone(title=title % "Búsqueda en Jayhap (Youtube, Vimeo & Dailymotion)",
                                   action="jayhap_search", text_color="green"))

    if item.contextual:
        global window_select, result
        select = Select("DialogSelect.xml", config.get_runtime_path(), item=item, itemlist=itemlist, caption="Buscando: "+item.contentTitle)
        window_select.append(select)
        select.doModal()

        if item.windowed:
            return result, window_select
    else:
        return itemlist


def manual_search(item):
    logger.info("streamondemand.channels.trailertools manual_search")
    texto = platformtools.dialog_input(default=item.contentTitle, heading=config.get_localized_string(30112))
    if texto is not None:
        if item.extra == "abandomoviez":
            return abandomoviez_search(item.clone(contentTitle=texto, page="", year=""))
        elif item.extra == "youtube":
            return youtube_search(item.clone(contentTitle=texto, page=""))
        elif item.extra == "filmaffinity":
            return filmaffinity_search(item.clone(contentTitle=texto, page="", year=""))
        elif item.extra == "jayhap":
            return jayhap_search(item.clone(contentTitle=texto))


def tmdb_trailers(item, tipo="movie"):
    logger.info("streamondemand.channels.trailertools tmdb_trailers")

    from core.tmdb import Tmdb
    itemlist = []
    tmdb_search = None
    if item.infoLabels['tmdb_id']:
        tmdb_search = Tmdb(id_Tmdb=item.infoLabels['tmdb_id'], tipo=tipo, idioma_busqueda='it')
    elif item.infoLabels['year']:
        tmdb_search = Tmdb(texto_buscado=item.contentTitle, tipo=tipo, year=item.infoLabels['year'])

    if tmdb_search:
        for result in tmdb_search.get_videos():
            title = result['name'] + " [" + result['size'] + "p] (" + result['language'].replace("en", "ING")\
                    .replace("es", "ESP")+")  [tmdb/youtube]"
            itemlist.append(item.clone(action="play", title=title, url=result['url'], server="youtube"))
    
    return itemlist


def youtube_search(item):
    logger.info("streamondemand.channels.trailertools youtube_search")
    itemlist = []

    titulo = item.contentTitle
    if item.extra != "youtube":
        titulo += " trailer"
    # Comprueba si es una búsqueda de cero o viene de la opción Siguiente
    if item.page != "":
        data = scrapertools.downloadpage(item.page)
    else:
        titulo = urllib.quote(titulo)
        titulo = titulo.replace("%20", "+")
        data = scrapertools.downloadpage("https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q="+titulo)

    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)
    patron = '<span class="yt-thumb-simple">.*?(?:src="https://i.ytimg.com/|data-thumb="https://i.ytimg.com/)([^"]+)"' \
             '.*?<h3 class="yt-lockup-title ">.*?<a href="([^"]+)".*?title="([^"]+)".*?' \
             '</a><span class="accessible-description".*?>.*?(\d+:\d+)'
    matches = scrapertools.find_multiple_matches(data, patron)
    for scrapedthumbnail, scrapedurl, scrapedtitle, scrapedduration in matches:
        scrapedthumbnail = urlparse.urljoin("https://i.ytimg.com/", scrapedthumbnail)
        scrapedtitle = scrapedtitle.decode("utf-8")
        scrapedtitle = scrapedtitle + " (" + scrapedduration + ")"
        if item.contextual:
            scrapedtitle = "[COLOR white]%s[/COLOR]" % scrapedtitle
        url = urlparse.urljoin('https://www.youtube.com/', scrapedurl)
        itemlist.append(item.clone(title=scrapedtitle, action="play", server="youtube", url=url,
                                   thumbnail=scrapedthumbnail, text_color="white"))
    
    next_page = scrapertools.find_single_match(data, '<a href="([^"]+)"[^>]+><span class="yt-uix-button-content">'
                                                     'Siguiente')
    if next_page != "":
        next_page = urlparse.urljoin("https://www.youtube.com", next_page)
        itemlist.append(item.clone(title=">> Siguiente", action="youtube_search", extra="youtube", page=next_page,
                                   thumbnail="", text_color=""))
    
    if not itemlist:
        itemlist.append(item.clone(title="La búsqueda no ha dado resultados (%s)" % titulo,
                                   action="", thumbnail="", text_color=""))

    if keyboard:
        if item.contextual:
            title = "[COLOR green]%s[/COLOR]"
        else: 
            title = "%s"
        itemlist.append(item.clone(title=title % "Búsqueda Manual en Youtube", action="manual_search",
                                   text_color="green", thumbnail="", extra="youtube"))

    return itemlist


def abandomoviez_search(item):
    logger.info("streamondemand.channels.trailertools abandomoviez_search")

    # Comprueba si es una búsqueda de cero o viene de la opción Siguiente
    if item.page != "":
        data = scrapertools.downloadpage(item.page)
    else:
        titulo = item.contentTitle.decode('utf-8').encode('iso-8859-1')
        post = urllib.urlencode({'query': titulo, 'searchby': '1', 'posicion': '1', 'orden': '1',
                                 'anioin': item.year, 'anioout': item.year, 'orderby': '1'})
        url = "http://www.abandomoviez.net/db/busca_titulo_advance.php"
        item.prefix = "db/"
        data = scrapertools.downloadpage(url, post=post)
        if "No hemos encontrado ninguna" in data:
            url = "http://www.abandomoviez.net/indie/busca_titulo_advance.php"
            item.prefix = "indie/"
            data = scrapertools.downloadpage(url, post=post).decode("iso-8859-1").encode('utf-8')

    itemlist = []
    patron = '(?:<td width="85"|<div class="col-md-2 col-sm-2 col-xs-3">).*?<img src="([^"]+)"' \
             '.*?href="([^"]+)">(.*?)(?:<\/td>|<\/small>)'
    matches = scrapertools.find_multiple_matches(data, patron)
    # Si solo hay un resultado busca directamente los trailers, sino lista todos los resultados
    if len(matches) == 1:
        item.url = urlparse.urljoin("http://www.abandomoviez.net/%s" % item.prefix, matches[0][1])
        item.thumbnail = matches[0][0]
        itemlist = search_links_abando(item)
    elif len(matches) > 1:
        for scrapedthumbnail, scrapedurl, scrapedtitle in matches:
            scrapedurl = urlparse.urljoin("http://www.abandomoviez.net/%s" % item.prefix, scrapedurl)
            scrapedtitle = scrapertools.htmlclean(scrapedtitle)
            itemlist.append(item.clone(title=scrapedtitle, action="search_links_abando",
                                       url=scrapedurl, thumbnail=scrapedthumbnail, text_color="white"))

        next_page = scrapertools.find_single_match(data, '<a href="([^"]+)">Siguiente')
        if next_page != "":
            next_page = urlparse.urljoin("http://www.abandomoviez.net/%s" % item.prefix, next_page)
            itemlist.append(item.clone(title=">> Siguiente", action="abandomoviez_search", page=next_page, thumbnail="",
                                       text_color=""))

    if not itemlist:
        itemlist.append(item.clone(title="La búsqueda no ha dado resultados", action="", thumbnail="",
                                   text_color=""))
    
        if keyboard:
            if item.contextual:
                title = "[COLOR green]%s[/COLOR]"
            else: 
                title = "%s"
            itemlist.append(item.clone(title=title % "Búsqueda Manual en Abandomoviez",
                                       action="manual_search", thumbnail="", text_color="green", extra="abandomoviez"))

    return itemlist


def search_links_abando(item):
    logger.info("streamondemand.channels.trailertools search_links_abando")

    data = scrapertools.downloadpage(item.url)
    itemlist = []
    if "Lo sentimos, no tenemos trailer" in data:
        itemlist.append(item.clone(title="No hay ningún vídeo disponible", action="", text_color=""))
    else:
        if item.contextual:
            progreso = platformtools.dialog_progress("Buscando en abandomoviez", "Cargando trailers...")
            progreso.update(10)
            i = 0
            message = "Cargando trailers..."
        patron = '<div class="col-md-3 col-xs-6"><a href="([^"]+)".*?' \
                 'Images/(\d+).gif.*?</div><small>(.*?)</small>'
        matches = scrapertools.find_multiple_matches(data, patron)
        if len(matches) == 0:
            trailer_url = scrapertools.find_single_match(data, '<iframe.*?src="([^"]+)"')
            if trailer_url != "":
                trailer_url = trailer_url.replace("embed/", "watch?v=")
                code = scrapertools.find_single_match(trailer_url, 'v=([A-z0-9\-_]+)')
                thumbnail = "https://img.youtube.com/vi/%s/0.jpg" % code
                itemlist.append(item.clone(title="Trailer  [youtube]", url=trailer_url, server="youtube",
                                           thumbnail=thumbnail, action="play", text_color="white"))
        else:
            for scrapedurl, language, scrapedtitle in matches:
                if language == "1":
                    idioma = " (ESP)"
                else:
                    idioma = " (V.O)"
                scrapedurl = urlparse.urljoin("http://www.abandomoviez.net/%s" % item.prefix, scrapedurl)
                scrapedtitle = scrapertools.htmlclean(scrapedtitle) + idioma + "  [youtube]"
                if item.contextual:
                    i += 1
                    message += ".."
                    progreso.update(10 + (90*i/len(matches)), message)
                    scrapedtitle = "[COLOR white]%s[/COLOR]" % scrapedtitle

                data_trailer = scrapertools.downloadpage(scrapedurl)
                trailer_url = scrapertools.find_single_match(data_trailer, 'iframe.*?src="([^"]+)"')
                trailer_url = trailer_url.replace("embed/", "watch?v=")
                code = scrapertools.find_single_match(trailer_url, 'v=([A-z0-9\-_]+)')
                thumbnail = "https://img.youtube.com/vi/%s/0.jpg" % code
                itemlist.append(item.clone(title=scrapedtitle, url=trailer_url, server="youtube", action="play",
                                           thumbnail=thumbnail, text_color="white"))
        
        if item.contextual:
            progreso.close()

    if keyboard:
        if item.contextual:
            title = "[COLOR green]%s[/COLOR]"
        else: 
            title = "%s"
        itemlist.append(item.clone(title=title % "Búsqueda Manual en Abandomoviez",
                                   action="manual_search", thumbnail="", text_color="green", extra="abandomoviez"))
    return itemlist


def filmaffinity_search(item):
    logger.info("streamondemand.channels.trailertools filmaffinity_search")

    if item.filmaffinity:
        item.url = item.filmaffinity
        return search_links_filmaff(item)

    # Comprueba si es una búsqueda de cero o viene de la opción Siguiente
    if item.page != "":
        data = scrapertools.downloadpage(item.page)
    else:
        params = urllib.urlencode([('stext', item.contentTitle), ('stype%5B%5D', 'title'), ('country', ''),
                                   ('genre', ''), ('fromyear', item.year), ('toyear', item.year)])
        url = "http://www.filmaffinity.com/es/advsearch.php?%s" % params
        data = scrapertools.downloadpage(url)

    itemlist = []
    patron = '<div class="mc-poster">.*?<img.*?src="([^"]+)".*?' \
             '<div class="mc-title"><a  href="/es/film(\d+).html"[^>]+>(.*?)<img'
    matches = scrapertools.find_multiple_matches(data, patron)
    # Si solo hay un resultado, busca directamente los trailers, sino lista todos los resultados
    if len(matches) == 1:
        item.url = "http://www.filmaffinity.com/es/evideos.php?movie_id=%s" % matches[0][1]
        item.thumbnail = matches[0][0]
        if not item.thumbnail.startswith("http"):
            item.thumbnail = "http://www.filmaffinity.com" + item.thumbnail
        itemlist = search_links_filmaff(item)
    elif len(matches) > 1:
        for scrapedthumbnail, id, scrapedtitle in matches:
            if not scrapedthumbnail.startswith("http"):
                scrapedthumbnail = "http://www.filmaffinity.com" + scrapedthumbnail
            scrapedurl = "http://www.filmaffinity.com/es/evideos.php?movie_id=%s" % id
            scrapedtitle = unicode(scrapedtitle, encoding="utf-8", errors="ignore")
            scrapedtitle = scrapertools.htmlclean(scrapedtitle)
            itemlist.append(item.clone(title=scrapedtitle, url=scrapedurl, text_color="white",
                                       action="search_links_filmaff", thumbnail=scrapedthumbnail))

        next_page = scrapertools.find_single_match(data, '<a href="([^"]+)">&gt;&gt;</a>')
        if next_page != "":
            next_page = urlparse.urljoin("http://www.filmaffinity.com/es/", next_page)
            itemlist.append(item.clone(title=">> Siguiente", page=next_page, action="filmaffinity_search", thumbnail="",
                                       text_color=""))

    if not itemlist:
        itemlist.append(item.clone(title="La búsqueda no ha dado resultados (%s)" % item.contentTitle,
                                   action="", thumbnail="", text_color=""))

        if keyboard:
            if item.contextual:
                title = "[COLOR green]%s[/COLOR]"
            else: 
                title = "%s"
            itemlist.append(item.clone(title=title % "Búsqueda Manual en Filmaffinity",
                                       action="manual_search", text_color="green", thumbnail="", extra="filmaffinity"))
        
    return itemlist


def search_links_filmaff(item):
    logger.info("streamondemand.channels.trailertools search_links_filmaff")
    
    itemlist = []
    data = scrapertools.downloadpage(item.url)
    if not '<a class="lnkvvid"' in data:
        itemlist.append(item.clone(title="No hay ningún vídeo disponible", action="", text_color=""))
    else:
        patron = '<a class="lnkvvid".*?<b>(.*?)</b>.*?iframe.*?src="([^"]+)"'
        matches = scrapertools.find_multiple_matches(data, patron)
        for scrapedtitle, scrapedurl in matches:
            if not scrapedurl.startswith("http:"):
                scrapedurl = urlparse.urljoin("http:", scrapedurl)
            trailer_url = scrapedurl.replace("-nocookie.com/embed/", ".com/watch?v=")
            if "youtube" in trailer_url:
                server = "youtube"
                code = scrapertools.find_single_match(trailer_url, 'v=([A-z0-9\-_]+)')
                thumbnail = "https://img.youtube.com/vi/%s/0.jpg" % code
            else:
                server = servertools.get_server_from_url(trailer_url)
                thumbnail = item.thumbnail
            scrapedtitle = unicode(scrapedtitle, encoding="utf-8", errors="ignore")
            scrapedtitle = scrapertools.htmlclean(scrapedtitle)
            scrapedtitle += "  [" + server + "]"
            if item.contextual:
                scrapedtitle = "[COLOR white]%s[/COLOR]" % scrapedtitle            
            itemlist.append(item.clone(title=scrapedtitle, url=trailer_url, server=server, action="play",
                                       thumbnail=thumbnail, text_color="white"))

    if keyboard:
        if item.contextual:
            title = "[COLOR green]%s[/COLOR]"
        else: 
            title = "%s"
        itemlist.append(item.clone(title=title % "Búsqueda Manual en Filmaffinity",
                                   action="manual_search", thumbnail="", text_color="green", extra="filmaffinity"))
    return itemlist


def jayhap_search(item):
    logger.info("streamondemand.channels.trailertools jayhap_search")
    itemlist = []

    if item.extra != "jayhap":
        item.contentTitle += " trailer"
    texto = item.contentTitle
    post = urllib.urlencode({'q': texto, 'yt': 'true', 'vm': 'true', 'dm': 'true',
                             'v': 'all', 'l': 'all', 'd': 'all'})

    # Comprueba si es una búsqueda de cero o viene de la opción Siguiente
    if item.page != "":
        post += urllib.urlencode(item.page)
        data = scrapertools.downloadpage("https://www.jayhap.com/load_more.php", post=post)
    else:
        data = scrapertools.downloadpage("https://www.jayhap.com/get_results.php", post=post)
    data = jsontools.load_json(data)
    for video in data['videos']:
        url = video['url']
        server = video['source'].lower()
        duration = " (" + video['duration'] + ")"
        title = video['title'].decode("utf-8") + duration + "  [" + server.capitalize() + "]"
        thumbnail = video['thumbnail']
        if item.contextual:
            title = "[COLOR white]%s[/COLOR]" % title
        itemlist.append(item.clone(action="play", server=server, title=title, url=url, thumbnail=thumbnail,
                                   text_color="white"))

    if not itemlist:
        itemlist.append(item.clone(title="La búsqueda no ha dado resultados (%s)" % item.contentTitle,
                                   action="", thumbnail="", text_color=""))
    else:
        tokens = data['tokens']
        tokens['yt_token'] = tokens.pop('youtube')
        tokens['vm_token'] = tokens.pop('vimeo')
        tokens['dm_token'] = tokens.pop('dailymotion')
        itemlist.append(item.clone(title=">> Siguiente", page=tokens, action="jayhap_search", extra="jayhap",
                                   thumbnail="", text_color=""))

    if keyboard:
        if item.contextual:
            title = "[COLOR green]%s[/COLOR]"
        else: 
            title = "%s"
        itemlist.append(item.clone(title=title % "Búsqueda Manual en Jayhap", action="manual_search",
                                   text_color="green", thumbnail="", extra="jayhap"))

    return itemlist

try:
    import xbmcgui
    import xbmc
    class Select(xbmcgui.WindowXMLDialog):
        def __init__(self, *args, **kwargs):
            self.item = kwargs.get('item')
            self.itemlist = kwargs.get('itemlist')
            self.caption = kwargs.get('caption')
            self.result = None

        def onInit(self):
            try:
                self.control_list = self.getControl(6)
                self.getControl(5).setNavigation(self.control_list, self.control_list, self.control_list, self.control_list)
                self.getControl(3).setEnabled(0)
                self.getControl(3).setVisible(0)
            except:
                pass

            try:
                self.getControl(99).setVisible(False)
            except:
                pass
            self.getControl(1).setLabel("[COLOR orange]"+self.caption+"[/COLOR]")
            self.getControl(5).setLabel("[COLOR tomato][B]Cerrar[/B][/COLOR]")
            self.items = []
            for item in self.itemlist:
                item_l = xbmcgui.ListItem(item.title)
                item_l.setArt({'thumb': item.thumbnail})
                item_l.setProperty('item_copy', item.tourl())
                self.items.append(item_l)
            self.control_list.reset()
            self.control_list.addItems(self.items)
            self.setFocus(self.control_list)

        def onClick(self, id):
            # Boton Cancelar y [X]
            if id == 5:
                global window_select, result
                self.result = "_no_video"
                result = "no_video"
                self.close()
                window_select.pop()
                if not window_select:
                    if not self.item.windowed:
                        del window_select
                else:
                    window_select[-1].doModal()


        def onAction(self,action):
            global window_select, result
            if action == 92 or action == 110:
                self.result = "no_video"
                result = "no_video"
                self.close()
                window_select.pop()
                if not window_select:
                    if not self.item.windowed:
                        del window_select
                else:
                    window_select[-1].doModal()

            try:
                if (action == 7 or action == 100) and self.getFocusId() == 6:
                    selectitem = self.control_list.getSelectedItem()
                    item = Item().fromurl(selectitem.getProperty("item_copy"))
                    if item.action == "play" and self.item.windowed:
                        video_urls, puede, motivo = servertools.resolve_video_urls_for_playing(item.server, item.url)
                        self.close()
                        xbmc.sleep(200)
                        if puede:
                            result = video_urls[-1][1]
                            self.result = video_urls[-1][1]
                        else:
                            result = None
                            self.result = None
                            
                    elif item.action == "play" and not self.item.windowed:
                        for window in window_select:
                            window.close()
                        retorna = platformtools.play_video(item)
                        if not retorna:
                            while True:
                                xbmc.sleep(1000)
                                if not xbmc.Player().isPlaying():
                                    break
                        window_select[-1].doModal()
                    else:
                        self.close()
                        buscartrailer(item)
            except:
                import traceback
                logger.info(traceback.format_exc())
except:
    pass
