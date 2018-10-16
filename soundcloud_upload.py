import requests
import time
import json
from requests_toolbelt import MultipartEncoder
import xml.etree.ElementTree as xml
import random


#AW SHOOT LOOKS LIKE THE SIGNATURE IS A VALUE THAT NEEDS TO STAY THE SAME FOR SOME REASON, MAYBE SHOULD SEE IF YOU CAN FIX THAT??


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
CLIENT_ID = "EGmCD3nEZiHAGZsCZxWyqLwEm365gx5W" #IF LOGIN BREAKS ITS LIKELY BECAUSE CLIENT_ID ISN'T ACTUALLY STATIC


class SoundcloudRequestException(Exception):
    pass


class SoundcloudSession(object):
    
    def __init__(self, username, password, signature): #starts a new SoundcloudSession by logging in
        self._url_params = "?client_id={client_id}&app_version={timestamp}&app_locale=en".format(
            client_id = CLIENT_ID,
            timestamp = round(time.time())
        ) #url parameters commonly used for soundcloud requests
        self._headers = {
            "user_agent": USER_AGENT,
        } #headers commonly used for soundcloud requests
        oauth_token = self._login(username, password, signature)
        self._headers["Authorization"] = "OAuth " + oauth_token
        

    def _request(self, method, url, url_params = None, exception = "", **request_params): #performs a request with some default headers and url parameters
        if "headers" not in request_params: #set headers to default if not specified
            request_params["headers"] = self._headers
        if url_params is None: #set url params to default if not specified
            url_params = self._url_params
        res = method(url + url_params, **request_params)
        if res.ok:
            return res
        exception = exception + " [Status code {}]\nheaders: {}\nurl: {}\n\nResponse content: {}".format(
            res.status_code, request_params["headers"], url + url_params, res.content
        ) 
        raise SoundcloudRequestException(exception)
        
        
    def _login(self, username, password, signature): #logs in and returns OAuth session token
        data = {  
            "client_id": CLIENT_ID, #if login breaks this is likely the problem: client id might not be static like I think it is
            "scope": "fast-connect non-expiring purchase signup upload",
            "recaptcha_pubkey": "6LeAxT8UAAAAAOLTfaWhndPCjGOnB54U1GEACb7N", #doesn't seem to change, hopefully that makes sense
            "recaptcha_response": None,
            "credentials": {  
                "identifier": username,
                "password": password
            },
            "signature": signature, #probably random ("8:33-1-5443-51-1049088-1046-2-2:7c7f46:2", 8:33-1-7732-103-1049088-1046-2-2:acb525:2")
            "device_id": "999097-819508-797553-478202", #also probably random ("999097-819508-797553-478202", "395883-699438-971858-587939")
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
        }
        res = self._request(requests.post,
            "https://api-v2.soundcloud.com/sign-in/password",
            exception = "Failed to log in", json = data
        )
        res_data = json.loads(res.content)
        return res_data["session"]["access_token"]

    
    def _get_upload_policy(self):
        res = self._request(requests.get,
            "https://api.soundcloud.com/upload/policy",
            exception = "Couldn't get upload policy"
        )
        return json.loads(res.content)


    def _upload(self, file_data, upload_policy):
        upload_policy["file"] = file_data
        upload_policy["Content-Disposition"] = "attachment;filename=\"\"" #if I don't set this and download the song it just has the name ${filename}$. This way amazon sets the filename to an empty string.
        data = MultipartEncoder(fields = upload_policy) #the only way to mime encode without a specifiying a files parameter in .post for some reason
        headers = {
            "user_agent": USER_AGENT,
            "Content-Type": data.content_type,
            "x-amz-server-side-encryption": "AES256",
            "x-amz-storage-class": "STANDARD_IA"        
        }
        res = self._request(requests.post,
            "https://soundcloud-upload.s3.amazonaws.com/",
            url_params = "",
            exception = "Couldn't upload file",
            headers = headers,
            data = data
        )
        xml_response = xml.ElementTree(xml.fromstring(res.content))
        return xml_response.find("Location").text


    def _transcode(self, uploaded_song_uid):
        extra_headers = {"Content-Type": "application/json"}
        res = self._request(requests.post,
            "https://api.soundcloud.com/transcodings",
            exception = "Transcoding post failed",
            headers = {**extra_headers, **self._headers},
            data = "uid=" + uploaded_song_uid
        )
        status_check_url = "https://api.soundcloud.com/transcodings/" + uploaded_song_uid
        while b'"status":"finished"' not in res.content: #keep checking transcode status until it's done
            time.sleep(0.5)
            res = self._request(requests.get,
                status_check_url,
                exception = "Couldn't check transcoding status"
            )


    def _post_track(self, upload_uid, title, description = "", genre = "", permalink = None, tags = [], public = True, downloadable = True):
        tags = ' '.join(tags)
        data = {
            "track": {  
                "api_streamable": True,
                "commentable": True,
                "description": description,
                "downloadable": downloadable,
                "embeddable": True,
                "feedable": False,
                "genre": genre,
                "isrc_generate": False,
                "license": "all-rights-reserved",
                "original_filename": "Angel.wav", #setting this does nothing noticable for some reason?
                "permalink": permalink, #for example: "delpls-1",
                "reveal_comments": True,
                "reveal_stats": True,
                "sharing": public,
                "tag_list": tags, #for example: "tag1 tag2",
                "title": title,
                "uid": upload_uid,
                "geo_blockings": [],
                "publisher_metadata": {  
                    "artist": None,
                    "album_title": None,
                    "contains_music": True,
                    "publisher": None,
                    "iswc": None,
                    "upc_or_ean": None,
                    "isrc": None,
                    "p_line": None,
                    "c_line": None,
                    "explicit": None,
                    "writer_composer": None,
                    "release_title": None
                },
                "restrictions": []
            }
        }
        res = self._request(requests.post,
            "https://api-v2.soundcloud.com/tracks",
            exception = "Couldn't post track",
            json = data
        )
        return json.loads(res.content)


    def update_track_img(self, track_id, img_data):
        res = self._request(requests.put,
            "https://api.soundcloud.com/tracks/" + str(track_id), 
            exception = "Couldn't update track image",
            files = [("track[artwork_data]", img_data)] #don't need to use toolbelt for this file upload, can just use requests
        )
        return res.content


    def upload_song(self, song_data, album_img_data = None, **track_params):
        policy = self._get_upload_policy()
        uploaded_file = self._upload(song_data, policy)
        uid = uploaded_file.split('/')[-1]
        self._transcode(uid)
        track_data = self._post_track(uid, **track_params)
        if album_img_data is not None:
            self.update_track_img(track_data['id'], album_img_data)
        return track_data


    def upload_file(self, file_location, img_location = None, **track_params):
        with open(file_location, 'rb') as song:
            file_data = song.read()
        if img_location is not None:
            with open(img_location, 'rb') as img:
                img_data = img.read()
        else:
            img_data = None
        return self.upload_song(file_data, img_data, **track_params)
