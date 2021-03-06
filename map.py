#! /usr/bin/env python
#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## Copyrights Etienne Chové <chove@crans.org> 2009                       ##
##                                                                       ##
## This program is free software: you can redistribute it and/or modify  ##
## it under the terms of the GNU General Public License as published by  ##
## the Free Software Foundation, either version 3 of the License, or     ##
## (at your option) any later version.                                   ##
##                                                                       ##
## This program is distributed in the hope that it will be useful,       ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of        ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         ##
## GNU General Public License for more details.                          ##
##                                                                       ##
## You should have received a copy of the GNU General Public License     ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>. ##
##                                                                       ##
###########################################################################

from bottle import route, request, template, response, redirect, abort, static_file
from tools import utils, query, query_meta, assets
import byuser
import errors
import datetime
import math, StringIO
from PIL import Image
from PIL import ImageDraw


def check_items(items, all_items):
    if items == None or items == 'xxxx':
        return all_items
    else:
        items = items.split(',')
        it = filter(lambda i: str(i)[0]+'xxx' in items, all_items)
        for i in items:
            try:
                n = int(i)
                it.append(n)
            except:
                pass
        return it


@route('/map')
def index_redirect():
    new_url = "map/"
    if request.query_string:
        new_url += "?"
        new_url += request.query_string
    redirect(new_url)

@route('/map/')
def index(db, lang):
    # valeurs par défaut
    params = { "lat":    46.97,
               "lon":    2.75,
               "zoom":   6,
               "item":   None,
               "level":  1,
               "source": '',
               "class":  '',
               "username": '',
               "country": '',
               "tags":    '',
               "fixable": None,
             }

    for p in ["lat", "lon", "zoom", "item", "level", "tags", "fixable"]:
        if request.cookies.get("last_" + p, default=None):
            params[p] = request.cookies.get("last_" + p)

    for p in ["lat", "lon", "zoom", "item", "useDevItem", "level", "source", "username", "class", "country", "tags", "fixable"]:
        if request.params.get(p, default=None):
            params[p] = request.params.get(p)

    for p in ["lat", "lon"]:
        params[p] = float(params[p])

    for p in ["zoom"]:
        params[p] = int(params[p])

    if not params.has_key("useDevItem"):
        params["useDevItem"] = ""

    tags = query_meta._tags(db, lang)
    tags_selected = {}
    tags_params = params["tags"].split(',')
    for t in tags:
      if t in tags_params:
        tags_selected[t] = " selected=\"selected\""
      else:
        tags_selected[t] = ""

    fixable_selected = {}
    fixable_selected['online'] = " selected=\"selected\"" if params["fixable"] and params["fixable"] == "online" else ""
    fixable_selected['josm'] = " selected=\"selected\"" if params["fixable"] and params["fixable"] == "josm" else ""

    all_items = []
    db.execute("SELECT item FROM dynpoi_item GROUP BY item;")
    for res in db.fetchall():
        all_items.append(int(res[0]))
    active_items = check_items(params["item"], all_items)

    level_selected = {}
    for l in ("_all", "1", "2", "3", "1,2", "1,2,3"):
        level_selected[l] = ""

    if params["level"] == "":
        level_selected["1"] = " selected=\"selected\""
    elif params["level"] in ("1", "2", "3", "1,2", "1,2,3"):
        level_selected[params["level"]] = " selected=\"selected\""

    categories = query_meta._categories(db, lang)

    item_tags = {}
    item_levels = {"1": set(), "2": set(), "3": set()}
    for categ in categories:
        for err in categ["item"]:
            for l in err["levels"]:
                item_levels[str(l)].add(err["item"])
            if err["tags"]:
                for t in err["tags"]:
                    if not item_tags.has_key(t):
                        item_tags[t] = set()
                    item_tags[t].add(err["item"])

    item_levels["1,2"] = item_levels["1"] | item_levels["2"]
    item_levels["1,2,3"] = item_levels["1,2"] | item_levels["3"]

    urls = []
    # TRANSLATORS: link to help in appropriate language
    urls.append(("byuser", _("Issues by user"), "../byuser/"))
    urls.append(("relation_analyser", _("Relation analyser"), "http://analyser.openstreetmap.fr/"))
    # TRANSLATORS: link to source code
    urls.append(("statistics", _("Statistics"), "../control/update_matrix"))

    helps = []
    helps.append((_("Contact"), "../contact"))
    helps.append((_("Help on wiki"), _("http://wiki.openstreetmap.org/wiki/Osmose")))
    helps.append((_("Copyright"), "../copyright"))
    helps.append((_("Sources"), "https://github.com/osm-fr?query=osmose"))
    helps.append((_("Translation"), "../translation"))

    sql = """
SELECT
    EXTRACT(EPOCH FROM ((now())-timestamp)) AS age
FROM
    dynpoi_update_last
ORDER BY
    timestamp
LIMIT
    1
OFFSET
    (SELECT COUNT(*)/2 FROM dynpoi_update_last)
;
"""
    db.execute(sql)
    delay = db.fetchone()
    if delay and delay[0]:
        delay = delay[0]/60/60/24
    else:
        delay = 0

    if request.session.has_key('user'):
        if request.session['user']:
            user = request.session['user']['osm']['user']['@display_name']
            user_error_count = byuser._user_count(db, user.encode('utf-8'))
        else:
            user = '[user name]'
            user_error_count = {1: 0, 2: 0, 3: 0}
    else:
        user = None
        user_error_count = None

    return template('map/index', categories=categories, lat=params["lat"], lon=params["lon"], zoom=params["zoom"],
        source=params["source"], username=params["username"], classs=params["class"], country=params["country"],
        item_tags=item_tags, tags_selected=tags_selected, tags=tags, fixable_selected=fixable_selected,
        item_levels=item_levels, level_selected=level_selected,
        active_items=active_items, useDevItem=params["useDevItem"],
        urls=urls, helps=helps, delay=delay, languages_name=utils.languages_name, translate=utils.translator(lang),
        website=utils.website, request=request, assets=assets.environment,
        user=user, user_error_count=user_error_count)


def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

@route('/map/heat/<z:int>/<x:int>/<y:int>.png')
def heat(db, z, x, y):
    x2,y1 = num2deg(x,y,z)
    x1,y2 = num2deg(x+1,y+1,z)

    params = query._params()
    params.bbox = [y1, x1, y2, x2]
    items = query._build_where_item(params.item, "dynpoi_item")

    db.execute("""
SELECT
    SUM((SELECT SUM(t) FROM UNNEST(number) t))
FROM
    dynpoi_item
WHERE
""" + items)
    max = db.fetchone()
    if max and max[0]:
        max = float(max[0])
    else:
        response.content_type = 'image/png'
        return static_file("images/tile-empty.png", root='static')

    join, where = query._build_param(None, None, params.bbox, params.source, params.item, params.level, params.users, params.classs, params.country, params.useDevItem, params.status, params.tags, params.fixable)
    join = join.replace("%", "%%")
    where = where.replace("%", "%%")

    COUNT=32

    sql = """
SELECT
    COUNT(*),
    (((lon-%(y1)s))*%(count)s/(%(y2)s-%(y1)s)-0.5)::int AS latn,
    (((lat-%(x1)s))*%(count)s/(%(x2)s-%(x1)s)-0.5)::int AS lonn
FROM
""" + join + """
WHERE
""" + where + """
GROUP BY
    latn,
    lonn
"""
    db.execute(sql, {"x1":x1, "y1":y1, "x2":x2, "y2":y2, "count":COUNT})
    im = Image.new("RGB", (256,256), "#ff0000")
    draw = ImageDraw.Draw(im)

    transparent_area = (0,0,256,256)
    mask = Image.new('L', im.size, color=255)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rectangle(transparent_area, fill=0)

    for row in db.fetchall():
        count, x, y = row
        count = int(math.log(count) / math.log(max / ((z-4+1+math.sqrt(COUNT))**2)) * 255)
        count = 255 if count > 255 else count
        r = [(x*256/COUNT,(COUNT-1-y)*256/COUNT), ((x+1)*256/COUNT-1,((COUNT-1-y+1)*256/COUNT-1))]
        mask_draw.rectangle(r, fill=count)

    im.putalpha(mask)
    del draw

    buf = StringIO.StringIO()
    im.save(buf, 'PNG')
    response.content_type = 'image/png'
    return buf.getvalue()


@route('/map/markers')
def markers(db, lang):
    params = query._params()

    if (not params.users) and (not params.source) and (params.zoom < 6):
        return

    params.limit = 200
    params.full = False

    expires = datetime.datetime.now() + datetime.timedelta(days=365)
    path = '/'.join(request.fullpath.split('/')[0:-1])
    response.set_cookie('last_lat', str(params.lat), expires=expires, path=path)
    response.set_cookie('last_lon', str(params.lon), expires=expires, path=path)
    response.set_cookie('last_zoom', str(params.zoom), expires=expires, path=path)
    response.set_cookie('last_level', str(params.level), expires=expires, path=path)
    response.set_cookie('last_item', str(params.item), expires=expires, path=path)
    response.set_cookie('last_tags', str(','.join(params.tags)) if params.tags else '', expires=expires, path=path)
    response.set_cookie('last_fixable', str(params.fixable) if params.fixable else '', expires=expires, path=path)

    return errors._errors_geo(db, lang, params)


@route('/tpl/popup.tpl')
def popup_template(lang):
    return template('map/popup', mustache_delimiter="{{={% %}=}}", website=utils.website)

@route('/tpl/editor.tpl')
def editor_template(lang):
    return template('map/editor', mustache_delimiter="{{={% %}=}}")
