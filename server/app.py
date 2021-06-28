from flask import Flask, request, abort
from google_images_download import google_images_download 
#from transformers import pipeline
from textblob import TextBlob
import requests
import json
import urllib
import textstat
from joblib import load
from dotenv import load_dotenv, dotenv_values
import os

load_dotenv()

app = Flask(__name__)

giresponse = google_images_download.googleimagesdownload() 

# clf = load("app/model.joblib")

def imageUrl(query):
    print(query)
    arguments = {"keywords": query.replace(',', '').replace('£', '$'),
                 "limit":1,
                 "no_download":True}
    urls = giresponse.download(arguments)
    return urls[0][query.replace(',', '').replace('£', '$')][0]

#summarizer = pipeline("summarization")

API_URL = "https://api-inference.huggingface.co/models/sshleifer/distilbart-cnn-6-6"
headers = {"Authorization": "Bearer " + os.environ["HUGGINGFACE_API_KEY"]}

def query(payload):
	data = json.dumps(payload)
	response = requests.request("POST", API_URL, headers=headers, data=data)
	return json.loads(response.content.decode("utf-8"))

def summarizer(text):
    return query(
        {
            "inputs": text,
            "parameters": {
                'max_length': 75,
                'min_length': 50
            }
        }
    )

@app.route('/', methods=['POST'])
def do():
    body = request.get_json()
    safe_query = body["query"].split(' ')
    safe_query = '+'.join(safe_query) 
    res = requests.get(f'https://newsdata.io/api/1/news?apikey={os.environ["NEWS_API_KEY"]}&q={safe_query}&language=en')
    results = res.json()["results"]
    return getData(results, 3)

@app.route('/today', methods=["GET"])
def todaysHeadlines():
   res = requests.get(f'https://newsdata.io/api/1/news?apikey={os.environ["NEWS_API_KEY"]}&language=en&q=politics')
   #res2 = requests.get(f'https://newsdata.io/api/1/news?apikey=pub_42213970ad6b67a6efb40d24a9038c93875&language=en&q=politics&page=2')
   results = res.json()["results"]
   #results.extend(res2.json()['results'])
   print(results)
   return getData(results, 3)
    
def getData(results, limit):
    summaries = []
    for result in results:
        text = ""
        if len(summaries) < limit and result["content"] and result['title'] not in [sum['headline'] for sum in summaries]:
            text = result["content"]

            image = ''
            if not result['image_url']:
                try:
                    image = imageUrl(result['title'])
                except:
                    image = None
            else:
                image = result['image_url']
            
            image = image.replace('http:', 'https:')

            if len(text) > 1024:
                text = text[:1024]

            summary = summarizer(text)#, max_length=200, min_length=90, do_sample=False)
            blob = TextBlob(summary[0]["summary_text"])
            summaries.append({
                "headline": result['title'] or '',
                "image": image or '',
                "source": result['source_id'] or '',
                "summary": summary[0]["summary_text"],
                "polarity": blob.sentiment[0],
                "subjectivity": blob.sentiment[1],
                "reading_level": textstat.flesch_reading_ease(summary[0]["summary_text"]),
                "article_url": result['link'],
                "political_leaning": 1 # int(clf.predict([summary[0]["summary_text"]])[0])
            })

       
    return {
        "articles": summaries
    }

if __name__ == '__main__':
    app.run(port=80)
