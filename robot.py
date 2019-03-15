from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
import traceback
import requests, urllib.parse
import csv
import json
from datetime import datetime
import os
import time
import random

SLACK_DICT = {
	'token': '',
	'channel': '',
	'text': '',
	'username': 'bot'
}
SLACK_URL = 'https://slack.com/api/chat.postMessage'
SLACK_NOTIFY = True
ERROR_COUNT = 0
URL_LIST = ['wiktionary',
'google', 
'youtube', 
'wikipedia', 
'baike.baidu.com',
'facebook.com']

def send_msg_slack(message):
	try:
		if not SLACK_NOTIFY:
			print(message)
			return
		SLACK_DICT['text'] = message
		r = requests.post(SLACK_URL, urllib.parse.urlencode(SLACK_DICT), headers={'Content-Type':'application/x-www-form-urlencoded'})
	except Exception as e:
		print(e)
		print(traceback.format_exc())


def get_search_url(query, page_num=0, per_page=10, lang='zh-TW'):
	query = quote_plus(query)
	# url = 'https://www.google.hr/search?q={}&num={}&start={}&nl={}'.format(query, per_page, page_num*per_page, lang)
	url = 'https://www.bing.com/search?q={}&first={}'.format(query,page_num*per_page+1)
	return url


def get_right_href(driver, search_string, page_num):
	global URL_LIST
	try:
		TIME_OUT = 300
		while TIME_OUT < 600:
			try:
				driver.get(get_search_url(search_string, page_num))
				driver.execute_script("window.alert = function() {};")
				WebDriverWait(driver, TIME_OUT).until(EC.presence_of_element_located((By.ID, 'b_results')))
				break
			except TimeoutException:
				send_msg_slack('Bing TimeoutException:'+str(TIME_OUT)+" "+search_string+" "+str(page_num)+" "+get_search_url(search_string, page_num))
				TIME_OUT += 60
		if TIME_OUT > 600:
			return ''
		a_list=driver.find_elements_by_xpath("//li[@class='b_algo']//h2/a")
		for element in a_list:
			href = element.get_attribute('href')
			if href.find("http://") == -1 and href.find("https://") == -1:
				continue
			b_rtn = True
			for url in URL_LIST:
				if href.find(url) != -1:
					b_rtn = False
			if b_rtn:
				URL_LIST += [href.split("/")[2]]
				return href
	except Exception as e:
		send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))
	SLEEP_TIME = random.randint(2,60)
	print("SLEEP TIME [href is empty]:"+str(SLEEP_TIME))
	time.sleep(SLEEP_TIME)
	return ''

def write_to_csv(search_string, url, error_msg):
	global ERROR_COUNT
	try:
		with open("result.csv", "a") as f:
			cw = csv.writer(f, delimiter=",")
			cw.writerow([search_string, url, error_msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
			ERROR_COUNT += 1
	except Exception as e:
		send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))

capabilities = DesiredCapabilities.CHROME
capabilities['loggingPrefs'] = { 'browser':'ALL' }

driver = webdriver.Chrome(desired_capabilities=capabilities)

try:
	fss = open("search_strings.json", "r")
	search_list = json.load(fss)
	done_list = []
	if os.path.isfile("search_done.json"):
		dict_done = json.load(open("search_done.json", "r"))
		done_list = dict_done.get("string", [])
		URL_LIST = dict_done.get("href", URL_LIST)
		ERROR_COUNT = dict_done.get("error", ERROR_COUNT)
		search_list = list(set(search_list)-set(done_list))
	with open("search_done.csv", "a") as fw:
		cw = csv.writer(fw, delimiter=",")
		cw.writerow(["Start", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
		send_msg_slack("Start:"+datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		for search_string in search_list:
			if ERROR_COUNT > 100:
				break
			if len(search_string) == 1:
				search_string = search_string + " " + done_list[random.randint(0, len(done_list)-1)]
			# wait 10 seconds
			href = ""
			page_num = 0
			while len(href) == 0:
				href = get_right_href(driver, search_string, page_num)
				page_num += 1
				if page_num > 10:
					break
			if len(href) == 0:
				send_msg_slack("len(href) == 0: "+search_string)
			else:
				try:
					driver.implicitly_wait(30)
					driver.get(href)
					driver.execute_script("window.alert = function() {};")
					driver.execute_script("window.stop();")
					for entry in driver.get_log('browser'):
						if entry.get("level") == 'SEVERE':
							write_to_csv(search_string, href, entry.get('message'))
							break
				except Exception as e:
					send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))
			done_list += [search_string]
			with open("search_done.json", "w") as fsd:
				json.dump({"string": done_list, "href": URL_LIST, "error": ERROR_COUNT}, fsd)
			cw.writerow([str(ERROR_COUNT)+"/"+str(len(done_list)),datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
			send_msg_slack(str(ERROR_COUNT)+"/"+str(len(done_list))+" : "+datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			SLEEP_TIME = random.randint(2,30)
			send_msg_slack("SLEEP TIME:"+str(SLEEP_TIME))
			time.sleep(SLEEP_TIME)
except Exception as e:
	send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))
finally:
	driver.quit()
with open("search_done.csv", "a") as fw:
	cw = csv.writer(fw, delimiter=",")
	cw.writerow(["End", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
