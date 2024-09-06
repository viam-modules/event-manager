import os
import shutil
import re
import asyncio
from PIL import Image
from viam.proto.app.data import Filter
import io

from viam.logging import getLogger

LOGGER = getLogger(__name__)

CAM_BUFFER_SIZE=75
ROOT_DIR = '/tmp'

def push_buffer(resources, cam_name, img):
    camera_buffer = _name_clean(cam_name)
    buffer_index_label = camera_buffer + '_buffer'
    if resources.get(buffer_index_label) == None:
        # set buffer position to 0
        resources[buffer_index_label] = 0
    else:
        resources[buffer_index_label] = resources[buffer_index_label] + 1
        if resources[buffer_index_label] >= CAM_BUFFER_SIZE:
            resources[buffer_index_label] = 0
    
    out_dir = ROOT_DIR + '/' + camera_buffer
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)
    img.save(out_dir + '/' + str(resources[buffer_index_label]) + '.jpg')

def copy_image_sequence(cam_name, event_name, event_id):
    camera_buffer = _name_clean(cam_name)
    src_dir = ROOT_DIR + '/' + camera_buffer
    out_dir = _label(event_name, camera_buffer, event_id, True)
    shutil.copytree(src_dir, out_dir)
    return out_dir

async def send_data(cam_name, event_name, event_id, app_client, part_id, path):
    start_index = _get_oldest_image_index(path)
    end_index = _get_greatest_image_index(path)
    index = start_index
    sent_all = False
    while sent_all == False:
        f = str(index) + '.jpg'
        im = Image.open(os.path.join(path, f))
        buf = io.BytesIO()
        im.save(buf, format='JPEG')
        await app_client.data_client.file_upload(component_name=cam_name, part_id=part_id, file_extension=".jpg", tags=[_label(event_name, cam_name, event_id, False)], data=buf.getvalue())
        index = index + 1
        if index == start_index:
            sent_all = True 
        if index > end_index:
            index = 0
    shutil.rmtree(path)
    return

def _get_oldest_image_index(requested_dir):
    mtime = lambda f: os.stat(os.path.join(requested_dir, f)).st_mtime
    return int(os.path.splitext(list(sorted(os.listdir(requested_dir), key=mtime))[0])[0])

def _get_greatest_image_index(requested_dir):
    index = lambda f: int(os.path.splitext(os.path.basename(os.path.splitext(os.path.join(requested_dir, f))[0]))[0])
    return int(os.path.splitext(list(sorted(os.listdir(requested_dir), key=index))[-1])[0])
    
async def get_triggered_filesystem(camera:str=None, event:str=None, num:int=5):
    pattern = _create_match_pattern(camera, event, None, True)
    dsearch = lambda f: (os.path.isdir(f) and re.match(pattern, f))
    ctime = lambda f: os.stat(os.path.join(ROOT_DIR, f)).st_ctime
    all_matched = sorted(filter(dsearch, [os.path.join(ROOT_DIR, f) for f in os.listdir(ROOT_DIR)]), key=ctime, reverse=True)
    matched = []
    if len(all_matched) < num:
        num = len(all_matched)
    for x in range(int(num)):
        spl = all_matched[x].split('--')
        matched.append({"event": spl[1].replace('_', ' '), "camera": spl[2], "time": spl[3], "id": all_matched[x].replace(ROOT_DIR + '/', '') })
    return matched

async def get_triggered_cloud(camera:str=None, event:str=None, num:int=5, app_client:str=None):
    pattern = _create_match_pattern(camera, event, None, False)
    filter_args = {}
    if camera:
        filter_args['component_name'] = camera
    tags = await app_client.data_client.tags_by_filter(Filter(**filter_args))
    matched = []
    for tag in tags:
        if re.match(pattern, tag):
            spl = tag.split('--')
            matched.insert(0, {"event": spl[1].replace('_', ' '), "camera": spl[2], "time": spl[3], "id": tag })
    return matched

async def delete_from_filesystem(camera:str=None, event:str=None, id:str=None):
    pattern = _create_match_pattern(camera, event, id, True)

    dsearch = lambda f: (os.path.isdir(f) and re.match(pattern, f))
    all_matched = list(filter(dsearch, [os.path.join(ROOT_DIR, f) for f in os.listdir(ROOT_DIR)]))
    for x in range(len(all_matched)):
        shutil.rmtree(all_matched[x])
    return len(all_matched)

# deletes tags from the cloud, not the actual images
async def delete_from_cloud(camera:str=None, event:str=None, id:str=None, app_client:str=None):
    pattern = _create_match_pattern(camera, event, id, False)
    filter_args = {}
    if camera:
        filter_args['component_name'] = camera
    tags = await app_client.data_client.tags_by_filter(Filter(**filter_args))
    matched = []
    for tag in tags:
        if re.match(pattern, tag):
            spl = tag.split('--')
            matched.append(tag)
    
    resp = await app_client.data_client.remove_tags_from_binary_data_by_filter(tags=matched, filter=Filter(**filter_args))
    return

def _name_clean(cam_name):
    return cam_name.replace(' ','_')

def _create_match_pattern(camera:str=None, event:str=None, id:str=None, use_filesystem:bool=False):
    prefix = ''
    if use_filesystem == True:
        prefix = ROOT_DIR + '/'
    pattern = prefix + 'SAVCAM--'
    if event != None:
        pattern = pattern + event + "--"
    else:
        pattern = pattern + ".*--"
    if camera != None:
        pattern = pattern + camera + "--.*"
    else:
        pattern = pattern + ".*--.*"
    if id != None:
        pattern = prefix + id
    return pattern

def _label(event_name, cam_name, event_id, use_filesystem):
    prefix = ''
    if use_filesystem:
        prefix = ROOT_DIR + '/'
    return _name_clean(f"{prefix}SAVCAM--{event_name}--{cam_name}--{event_id}")