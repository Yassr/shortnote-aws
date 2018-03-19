import datetime
import json
import math
import os
import re
from difflib import SequenceMatcher
import requests
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from ffmpy import FFmpeg

import wordcount


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
            request.session['file_extentionV'] = file_extentionV
            request.session['uploaded_file_url'] = uploaded_file_url
            return render(request, 'uploads/home.html', {
            'file_extentionV': file_extentionV, 'uploaded_file_url': uploaded_file_url})

    return render(request, 'uploads/home.html')


def video_clip(request):

    '''This is the Video Split Function'''
    short_url = request.session.get('uploaded_file_url')
    cut_url = short_url[1:]
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MEDIA_ROOT = os.path.join(BASE_DIR, '').replace('\\','/')

    full_url = MEDIA_ROOT[2:]+cut_url
    output_url = (MEDIA_ROOT+cut_url)[:-4] + '.flac'

    ve = FFmpeg(
        inputs={full_url: None},
        outputs={output_url: ['-y', '-f', 'flac', '-ab', '192000', '-vn']}
    )
    # print(ve.cmd)
    ve.run()

    '''This is the Transcription Function'''
    tr = open("output.json", "w+")
    audio_url = open(output_url, "rb")
    response = requests.post("https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?timestamps=true",
                             auth=("f7c2c504-fa84-4134-bf08-916409f4d53a", "3STmtCX6PaUM"),
                             headers={"Content-Type": "audio/flac"},
                             data=audio_url
                             )
    tr.write(response.text)
    # print("\nResponse is\n" + response.text + "\nAudio_url=" + str(output_url))
    tr.close()

    '''This is the Extract Text Function'''
    data = json.load(open('output.json'))
    et = open("sentences.txt", "w+")

    for alt_result in data["results"]:
        for transcription in alt_result["alternatives"]:
            # By substituting fullstops with a space it prevents unexpected end of sentence when summarizing
            # print(transcription["transcript"])
            nstr = re.sub(r'[.]', r'', transcription["transcript"])
            et.write(nstr + '.\n')
    et.close()

    sample = open('sentences.txt').read()
    stop_words = set(open('resources/stopwords.txt').read().split())

    f = open("summary.txt", "w+")

    caps = "([A-Z])"
    prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
    suffixes = "(Inc|Ltd|Jr|Sr|Co)"
    starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
    acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
    websites = "[.](com|net|org|io|gov)"

    def get_sentences(text):
        text = " " + text + "  "
        text = text.replace("\n", " ")
        text = re.sub(prefixes, "\\1<prd>", text)
        text = re.sub(websites, "<prd>\\1", text)
        if "Ph.D" in text: text = text.replace("Ph.D.", "Ph<prd>D<prd>")
        text = re.sub("\s" + caps + "[.] ", " \\1<prd> ", text)
        text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
        text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]", "\\1<prd>\\2<prd>\\3<prd>", text)
        text = re.sub(caps + "[.]" + caps + "[.]", "\\1<prd>\\2<prd>", text)
        text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
        text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
        text = re.sub(" " + caps + "[.]", " \\1<prd>", text)
        if "\"" in text: text = text.replace(".\"", "\".")
        if "!" in text: text = text.replace("!\"", "\"!")
        if "?" in text: text = text.replace("?\"", "\"?")
        text = text.replace(".", ".<stop>")
        text = text.replace("?", "?<stop>")
        text = text.replace("!", "!<stop>")
        text = text.replace("<prd>", ".")
        sentences = text.split("<stop>")
        sentences = sentences[:-1]
        sentences = [s.strip() for s in sentences]
        return sentences

    def get_score(sentence, word_scores):
        score = 0
        words = sentence.split()
        for word in words:
            if word not in stop_words:
                score += word_scores[word]
        return score

    word_scores = wordcount.get_word_frequency(sample, stop_words)
    sentences = get_sentences(sample)
    scores = {}
    for indx, sentence in enumerate(sentences):
        scores[sentence] = get_score(sentence, word_scores)

    sorted_scores = list(scores.values())
    sorted_scores.sort()
    n = int(round(0.5 * sorted_scores.__len__() + 0.5))
    cutoff = sorted_scores[n - 1]

    for sentence in sentences:
        if scores[sentence] > cutoff:
            # print(sentence)
            f.write(sentence + '\n')
    f.close()
    summryText = open("summary.txt", "r")

    def similar(a, b):
        return SequenceMatcher(None, a, b).ratio()
    the_final_mp4 = ''
    timegroup = []
    timecrop = []
    concat_list = []
    all_lines = []
    count = 0
    for s in summryText:
        print(s)
        all_lines.append(s)
        for alt_result in data['results']:
            # print(alt_result)
            for transcription in alt_result["alternatives"]:
                # print(similar(s, transcription["transcript"]))
                if similar(s, transcription["transcript"]) >= 0.99:
                    # print(transcription["transcript"])
                    timegroup = transcription["timestamps"]
                    # print(timegroup)
                    startwords = timegroup[0]
                    endwords = timegroup[-1]
                    # print(startwords)
                    # print(endwords)
                    starttimes = math.trunc((startwords[1:])[0])

                    endtimes = math.ceil((endwords[1:])[1])
                    # print(starttimes, endtimes)

                    addtimes = endtimes - starttimes

                    startHour = str(datetime.timedelta(seconds=starttimes))
                    endHour = str(datetime.timedelta(seconds=endtimes))
                    addHour = str(datetime.timedelta(seconds=addtimes))
                    print(startHour, endHour, addHour)
                    count = count + 1

                    # Split the video using the timestamps
                    ff = FFmpeg(
                        inputs={full_url: None},
                        outputs={'cut/part'+str(count)+'.ts': ['-y', '-ss', startHour, '-t', addHour, '-async', '1', '-strict', '-2']}
                    )
                    ff.run()

                    # Merge all cut parts of video together
                    concat = 'concat:cut/part' + str(count) + '.ts|'
                    concat_list.append(concat)
                    # print (concat_list)

                    shortnote_ts = os.path.join(BASE_DIR, '').replace('\\', '/') + "media/output.ts"
                    fm = FFmpeg(
                        inputs={"".join(concat_list): None},
                        outputs={shortnote_ts: ['-y', '-codec', 'copy']}
                    )
                    fm.run()
                    shortnote_ts_url = shortnote_ts

    shortnote_mp4 = shortnote_ts_url[:-3] + ".mp4"
    vt = FFmpeg(
        inputs={shortnote_ts_url: None},
        outputs={shortnote_mp4: ['-y', '-c:v', 'libx264', '-preset', 'medium', '-crf', '0']}
    )
    vt.run()

    cut_len = len(" /media/output.ts")
    shortnote_mp4 = shortnote_mp4[-cut_len:]
    the_final_mp4 = shortnote_mp4
    print(shortnote_mp4)
    all_lines = "\n".join(all_lines)
    return render(request, 'uploads/summary.html', {'uploaded_file_url': short_url, 'audio_url': output_url, 'the_final_mp4':the_final_mp4, 'all_lines':all_lines})
