"""
     _       _        _      
    (_)     | |      | |     
     _ _ __ | |_ ___ | | __  
    | | '_ \| __/ _ \| |/ /  
    | | | | | || (_) |   < _ 
    |_|_| |_|\__\___/|_|\_(_)    

    intok bypasses tiktok country restrictions (& and does not spy on you)
    made by https://github.com/jakubone (jakub.one)    

    web: tok.jakub.one
"""

from mdb import DB
import pyktok as pyk
import os
import inspect
import shutil
import random
import string
import math
from flask import Flask, render_template, request, send_from_directory, abort, redirect
import json
import threading
import config

pyk.specify_browser('chrome')

app = Flask(__name__, static_url_path='/assets', static_folder='assets')

def generate_random_name(length=8):
    return ''.join(random.choices('abcdef0123456789', k=length))

def move_files_with_phrase(src_folder, phrase, dest_folder='/videos', prefix=None):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    
    for filename in os.listdir(src_folder):
        if phrase in filename:
            random_name = prefix + os.path.splitext(filename)[1]
            src_path = os.path.join(src_folder, filename)
            dest_path = os.path.join(dest_folder, prefix)
            shutil.move(src_path, dest_path)
            print(f'[*] moved {filename} -> {dest_path}')

pyk.specify_browser('chrome')

db_path = './cached/'
db = DB(db_path)

def getVideo(vid):
    tt_json = pyk.alt_get_tiktok_json(vid)
    vid_id = None
    required_download = True
    cvid = generate_random_name(6)
    
    if "item doesn't exist" in tt_json:
        return {'error': True, 'message': "Video does not exist. (404)"}

    if "vm.tiktok.com" in vid:
        vid_id = vid.split('.com/')[1][:-1]
    elif "/video/" in vid:
        vid_id_tmp = vid.split('/video/')
        if "?" in vid_id_tmp[1]:
            vid_id = vid_id_tmp[1].split('?')[0]
        else:
            vid_id = vid_id_tmp[1]

    print(f"[*] parsed video id: {vid_id}")
    if db.get(f'{vid_id}'):
        print('[*] record found, no download required')
        required_download = False

    scraped_region = tt_json['__DEFAULT_SCOPE__']['webapp.app-context']['region'] # scraped via which region
    scraped_lang = tt_json['__DEFAULT_SCOPE__']['webapp.app-context']['language'] # scraped language
    scraped_info = f"Scraped via region-{scraped_region.lower()} (lang-{scraped_lang.lower()})" # formed string

    scraped_music = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['music']
    scraped_music_dl = scraped_music['playUrl']
    scraped_music_title = scraped_music['title']
    scraped_music_id = scraped_music['id']
    scraped_music_author = scraped_music['authorName']
    scraped_music_cover = scraped_music['coverLarge']
    scraped_is_org = scraped_music['original']

    music = {
        'id': scraped_music_id,
        'title': scraped_music_title,
        'author': scraped_music_author,
        'original': scraped_is_org,
        'cover': scraped_music_cover,
        'downloadurl': scraped_music_dl
    }

    scraped_stats = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['stats']
    scraped_desc = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['desc']
    scraped_createtime = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['createTime']
    scraped_labels = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['diversificationLabels']
    scraped_where_created = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['locationCreated']

    scraped_author = tt_json["__DEFAULT_SCOPE__"]['webapp.video-detail']['itemInfo']['itemStruct']['author']

    if required_download == False:
        cid = db.get(f"{vid_id}")

        res = {
            'id': cid['id'],
            'video_id': vid_id,
            'info': scraped_info,
            'vid_music': music,
            'stats': scraped_stats,
            'description': scraped_desc,
            'createtime': scraped_createtime,
            'creation_country': scraped_where_created,
            'author': scraped_author,
            'filename': f'/source/{cid["id"]}.mp4'
        }

        db.set(f"{vid_id}", res)
        db.set(f"{cid['id']}", res)

        print(f'[*] scraped data [tiktok id: {vid_id}] updated record: {cid["id"]}')
    else:
        res = {
            'id': cvid,
            'video_id': vid_id,
            'info': scraped_info,
            'vid_music': music,
            'stats': scraped_stats,
            'description': scraped_desc,
            'createtime': scraped_createtime,
            'creation_country': scraped_where_created,
            'author': scraped_author,
            'filename': f'/source/{cvid}.mp4'
        }

        db.set(f"{vid_id}", res)
        db.set(f"{cvid}", res)

        print(f'[*] scraped data [tiktok id: {vid_id}] created record: {cvid}')
        pyk.save_tiktok(vid,True)
        move_files_with_phrase("./", vid_id, './videos', cvid+'.mp4')

    print('[+] successfully scraped all data.')
    return cvid, vid_id

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_folder_statistics(folder='./videos'):
    total_files = 0
    total_size = 0
    
    for root, dirs, files in os.walk(folder):
        for file in files:
            total_files += 1
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
    
    human_readable_size = convert_size(total_size)
    
    return total_files, total_size, human_readable_size

"""
Webserver section here
"""

@app.route('/stats')
def stats():
    total_files, total_size, human_readable_size = get_folder_statistics()
    return {
        'total_files': total_files,
        'total_size': total_size,
        'human_readable_size': human_readable_size
    }

@app.route('/source/<id>')
def get_video(id):
    try:
        return send_from_directory('./videos', id)
    except FileNotFoundError:
        abort(404)
    
@app.route('/')
def m():
    return render_template('index.html')

@app.route('/<stid>')
def index(stid):
    if len(stid) > 9:
        return render_template('error.html', msg="Quick preview does not accept long urls.")

    res = db.get(f"{stid}")

    print(len(stid), stid)

    if res:
        return render_template('display.html', data=res)
    else:
        print(len(stid), stid)
        if len(stid) == 9:
            url = f'https://vm.tiktok.com/{stid}/'
        getVideo(url)

        return render_template('parsing.html', id=stid)

@app.route('/add')
def process_video():
    url = request.args.get('url', '')
    vid = request.args.get('url', '')

    if "vm.tiktok.com" in vid:
        vid_id = vid.split('.com/')[1][:-1]
    elif "/video/" in vid:
        vid_id_tmp = vid.split('/video/')
        if "?" in vid_id_tmp[1]:
            vid_id = vid_id_tmp[1].split('?')[0]
        else:
            vid_id = vid_id_tmp[1]

    chkvid = db.get(f"{vid_id}")

    if chkvid:
        return redirect(f"/{chkvid['id']}", code=302)

    if url == '':
        return render_template('error.html', msg="No URL provided")
    if "tiktok.com" not in url:
        return render_template('error.html', msg="Provided URL is not a TikTok URL.")

    cvid, vid_id = getVideo(url)
    return render_template('processed.html', msg="File has been processed.", vid_id=cvid, proto=config.protocol, domain=config.self_domain)


app.run(port=config.webserver_port)