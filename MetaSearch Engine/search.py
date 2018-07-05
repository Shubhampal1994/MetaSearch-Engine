from queue import Queue, Empty
from collections import defaultdict
from threading import Thread
import time
import re
from flask import render_template, request, redirect, url_for, Flask
import requests
from bs4 import BeautifulSoup


app = Flask(__name__)


@app.route('/')
def hello():
    return render_template('search.html')


@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    try:
        if len(query.strip()) > 0:
            t0 = time.time()
            candidates = _fetch_results(query)
            results = _merge(candidates)  # Variable 'results' stores the final output.
            # We can use this output for any further operations like Clustering...
            t1 = time.time()
            print("Query Execution Time: %f" % (t1 - t0))
            return render_template('results.html',
                                   result=results)
        return redirect(url_for('hello'))
    except Exception as E:
        error = 'No search results found for ' + query + "  " + str(E)
        return render_template('results.html', error=error)


def _fetch_results(query):
    query = _format_query(query)
    q = Queue()
    threads = [Thread(target=get_google_results(query, q)),
               Thread(target=get_bing_results(query, q)),
               Thread(target=get_yahoo_results(query, q)),
               ]
    for t in threads:
        t.start()
        t.join()
    return queue_get_all(q)


def _format_query(query):
    query = re.sub(r'[^\w\s]', ' ', query).lower()
    tokens = re.split(r'\s+', query)
    tokens = [token.strip() for token in tokens]
    return '+'.join(tokens)


def _merge(candidates):
    retrieved_docs = []
    for doc in candidates:
        retrieved_docs.append(doc)
    results = defaultdict(list)
    for doc in retrieved_docs:
        results[doc['source']].append(doc)
    return results


def queue_get_all(q):
    items = []
    max_cnt = 30
    cnt = 0
    while cnt < max_cnt:
        try:
            items.append(q.get(True, 2))
            cnt += 1
        except Empty:
            break
    return items


def get_google_results(query, queue):
    url = "http://www.google.com/search?q=%s" % query
    res = requests.get(url)
    if res.status_code == requests.codes.ok:
        results = BeautifulSoup(res.text).find_all('div', {'class': 'g'})
        for result in results:
            try:
                title = result.find('h3', {'class': 'r'}).getText()
                link = _format_google_url(result.find('h3', {'class': 'r'}).find(
                    'a', href=True)['href'])
                snippet_tag = result.find('span', {'class': 'st'})
                snippet = '' if snippet_tag is None else snippet_tag.getText()
                queue.put({'link': link, 'title': title, 'snippet': snippet, 'source': 'google'})
            except:
                queue.put({'link': 'No link found', 'title': 'None',
                           'snippet': 'No data', 'source': 'google'})


def get_bing_results(query, queue):
    url = "http://www.bing.com/search?q=%s" % query
    res = requests.get(url)
    if res.status_code == requests.codes.ok:
        results = BeautifulSoup(res.text, 'html').find_all('li', {'class': 'b_algo'})
        for result in results:
            try:
                title = result.find('h2').text
                link = result.find('h2').find('a')['href']
                snippet = result.find('p').text
                queue.put({'link': link, 'title': title, 'snippet': snippet, 'source': 'bing'})
            except:
                queue.put({'link': 'No link found', 'title': 'None',
                           'snippet': 'No data', 'source': 'bing'})


def get_yahoo_results(query, queue):
    url = "http://search.yahoo.com/search?p=%s" % query
    res = requests.get(url)
    if res.status_code == requests.codes.ok:
        results = BeautifulSoup(res.text, 'html').find_all('div',{'class': 'dd algo algo-sr Sr'})
        for result in results:
            try:
                title = result.find('h3').getText()
                link = _format_url(result.find('h3').find('a', href=True)['href'])
                snippet_tag = result.find('div', {'class': 'compText aAbs'})
                if snippet_tag == None:
                    snippet = ''
                else:
                    snippet = snippet_tag.getText()
                queue.put({'link': link, 'title': title, 'snippet': snippet, 'source': 'yahoo'})
            except:
                queue.put({'link': 'No link found', 'title': 'None',
                           'snippet': 'No data', 'source': 'yahoo'})


def _format_url(url):
    return url.strip().rstrip('/')


def _format_google_url(url):
    if url.startswith('/'):
        return "http://www.google.com" + url
    else:
        return url.strip().rstrip('/')


if __name__ == '__main__':
    app.run(debug=True)
