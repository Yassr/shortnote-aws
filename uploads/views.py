from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import subprocess




# Create your views here.
def home(request):
    return render(request, 'uploads/home.html')


def simple_upload(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)
        if uploaded_file_url.endswith('.mp3'):
            file_extentionA = '.mp3'
            return render(request, 'uploads/home.html', {
            'file_extentionA': file_extentionA, 'uploaded_file_url': uploaded_file_url})
        elif uploaded_file_url.endswith('.mp4'):
            file_extentionV = '.mp4'
            return render(request, 'uploads/home.html', {
            'file_extentionV': file_extentionV, 'uploaded_file_url': uploaded_file_url})
    return render(request, 'uploads/home.html')


def video_clip(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)


        # result = subprocess.Popen(["ffprobe", uploaded_file_url],
        #                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # videoSize = [x for x in result.stdout.readlines() if "Duration" in x]


        # ffmpeg_extract_subclip(uploaded_file_url, '00:00:02', '00:00:04', targetname="/shortnote/media/test.mp4")

        # subprocess.call(['ffmpeg', '-i', uploaded_file_url], stdout=videoduration)
        #
        # str = "ffmpeg -ss 00:00:30 -i "+uploaded_file_url+" -t 00:00:05 -vcodec copy -acodec copy "+videoduration
        # InfoLong = subprocess.check_output(str, shell=True).split("\n")
        # for info in InfoLong:
        #     if "duration" in info:
        #         print(info)
        #         videoduration = (info)
        videoduration = subprocess.check_output('ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '+uploaded_file_url+' -sexagesimal', stdout=videoduration)

        return render(request, 'uploads/home.html',{
            "video_size": videoduration
        })


        # subprocess.call(['ffmpeg', '-i', uploaded_file_url, '-ss', seconds, outputfilename])