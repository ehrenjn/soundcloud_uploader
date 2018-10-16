# soundcloud_uploader
Uploads songs to Soundcloud from Python using requests

### Logging in

To log into a Soundcloud account: `session = SoundcloudSession(username, password, signature)`  
The creation of a session requires a username, password and a _signature_ which is some strange paramter that I could not find the origin of, sadly :( 

To find your account signature you must first fire up your browser's debugger tools and start recording network traffic. 
Then, log in to your soundcloud account while recording your network traffic. 
Once you are logged into your account your browser's debugger should have logged a POST request to the url https://api-v2.soundcloud.com/sign-in/password.
The POST request should have a json payload that contains your username password and signature. 
Copy your signature and don't lose it. You only have to get this value once.  

The signature should be a string that looks something like: "9:69-1-87591-118-9671789-9572-1-2:da9856:5"

### Uploading a track

To upload a track call either `SoundcloudSession.upload_song` or `SoundcloudSession.upload_file`.  
`upload_file` uploads whatever file name you give it. `upload_song` uploads a byte string.  
both methods also have a `album_img` or `album_img_data` parameter that allows you to upload an album image along with the track.  

You must also specify a `title` when you upload a track. A title must be a string that meets the requirements for a Soundcloud song title.  
Other optional paramters are:  

| parameter    | type            | default |
|--------------|-----------------|---------|
| description  | string          | ""      |
| genre        | string          | ""      |
| permalink    | string          | None    |
| tags         | list of strings | []      |
| public       | boolean         | True    |
| downloadable | boolean         | True    |

upload_file example:  
`session.upload_file("song.wav", "img.png", title = "New song", description = "Top notch desc", genre = "good music", permalink = "upload_example", tags = ["tag1", "tag2"], public = True, downloadable = True)`
