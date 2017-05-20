# -*- coding: utf-8 -*-
import redis
import json
import os
import dat_service
import monitor_settings
import url_extract_tools
from flask import Flask, render_template, jsonify, request, current_app, redirect
from gen_spiderInitfile import generate_spider_init

app = Flask(__name__)


@app.route('/')
def index():
    return redirect('/static/index.html')


@app.route('/monitor')
def monitor():
    return render_template('index.html',
                           timeinterval=monitor_settings.TIMEINTERVAL,
                           stats_keys=monitor_settings.STATS_KEYS,
                           spider_name=request.args.get('spider_name'))


@app.route('/ajax')
def ajax():
    key = request.args.get('key')
    result = current_app.r.lrange(key, -monitor_settings.POINTLENGTH, -1)[::monitor_settings.POINTINTERVAL]
    if not current_app.spider_is_run:
        # spider is closed
        return json.dumps(result).replace('"', ''), 404
    return json.dumps(result).replace('"', '')


@app.route('/signal')
def signal():
    signal = request.args.get('sign')
    if signal == 'closed':
        current_app.spider_is_run = False
    elif signal == 'running':
        current_app.spider_is_run = True
    return jsonify('')


@app.route('/gen_spider', methods=['GET', 'POST'])
def gen_spider():
    jsonstr = request.form.get('json_result', '')
    js = dict(json.loads(jsonstr))
    start_urls = list(js['start_urls'])
    spider_name = url_extract_tools.extract_main_url(start_urls)
    dat_service.save_data(spider_name, jsonstr)
    generate_spider_init(jsonstr)
    return jsonify('ok')


@app.route('/add_ips', methods=['GET', 'POST'])
def add_ips():
    jsonstr = request.form.get('ips', '')
    ips_array = json.loads(jsonstr)['ips']
    dat_service.save_proxys(ips_array)
    return jsonify('ok')


@app.route('/target_urls', methods=['GET', 'POST'])
def target_urls():
    jsonstr = request.form.get('urls', '')
    urls_array = json.loads(jsonstr)['urls']
    dat_service.split_target_urls(urls_array)
    for filename in os.listdir(os.getcwd() + '/monitor/spiderinit_files'):
        if 'spiderInit_' in filename:
            print filename
            os.system('python ' + os.getcwd() + '/monitor/spiderinit_files/' + filename)
    return jsonify('ok')


@app.route('/get_spider_names', methods=['GET'])
def get_spider_names():
    return jsonify(dat_service.get_spider_count_from_db())


@app.before_first_request
def init():
    current_app.r = redis.Redis(host=monitor_settings.REDIS_HOST, port=monitor_settings.REDIS_PORT, db=monitor_settings.MONITOR_DB)
    if current_app.r.get('spider_is_run') == '1':
        current_app.spider_is_run = True
    else:
        current_app.spider_is_run = False


if __name__ == '__main__':
    #产生包含ip和port的js文件
    text = 'POST_URL_PREFIX = "http://' + monitor_settings.APP_HOST + ':' + str(monitor_settings.APP_PORT) + '"'
    filename = os.getcwd() + "/monitor/static/const.js"
    with open(filename, 'w') as f:
        f.write(text.encode('utf8'))
    app.run(host=monitor_settings.APP_HOST, port=monitor_settings.APP_PORT, debug=False)