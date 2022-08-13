from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from collections import defaultdict


import concurrent.futures as cf

from multiprocessing.pool import ThreadPool as Pool

import json
import time
from datetime import datetime 
import os
import sys
import re 
import pandas as pd
import threading
import argparse 

SAVE_DIR = '../outputs/'
SCREEN_DIR = '../screenshots/'
DELAY_TIME = 3
MAX_POST = None
MAX_CMT = 5
SCRAP_CMT = None

R = re.compile(r'#[a-zA-Z\d]+')

LOG_FILE_T1 = '../logs/log_thread_1.dat'
LOG_FILE_T2 = '../logs/log_thread_2.dat'
LOG_FILE_T3 = '../logs/log_thread_3.dat'
LOG_FILE_T4 = '../logs/log_thread_4.dat'
LOG_FILE_T5 = '../logs/log_thread_5.dat'


class Reply:
    def __init__(self):
        self.user = str
        self.date = str
        self.likes = []
        self.content = str


class Comment:
    def __init__(self):
        self.user = ''
        self.date = ''
        self.likes = []
        self.content = ''
        self.reply = []


class Post:
    def __init__(self):
        self.url = ''
        self.user = ''
        self.date = ''
        self.likes = []
        self.content = ''
        self.comment = []
        self.hashtag = []


def save_json(list_post, input_user):
    """ Save post information to JSON file"""

    def get_reply_to_json(replies):
        if len(replies) == 0:
            return {}
        else:
            reply_dict = []
            for r in replies:
                reply = {
                    'user': r.user,
                    'likes': r.likes,
                    'date': r.date,
                    'content': r.content
                }
                reply_dict.append(reply)
        return reply_dict

    def get_comment_to_json(cmt):
        if len(cmt) == 0:
            return {}
        else:
            comment_dict = []
            for c in cmt:
                comment = {
                    'user': c.user,
                    'likes': c.likes,
                    'date': c.date,
                    'content': c.content,
                    'reply': get_reply_to_json(c.reply)
                }
                comment_dict.append(comment)
        return comment_dict

    file_name = SAVE_DIR + input_user + ".json"

    final_list = []

    for post in list_post:
        post_dict = {
            'url': post.url,
            'user': post.user,
            'likes': post.likes,
            'date': post.date,
            'content': post.content,
            'comment': get_comment_to_json(post.comment),
            'hashtag': post.hashtag
        }
        final_list.append(post_dict)

    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)


def convert_reaction_num(text):
    if 'K' in text:
        return int(float(text[:-1])*1000)
    if 'M' in text:
        return int(float(text[:-1])*1000000)
    return int(text)


def convert_reaction(reaction_num, reaction_type):
    reaction_dict = {}
    for i, r in enumerate(reaction_type):
        reaction_dict[r] = convert_reaction_num(reaction_num[i])
    return reaction_dict


def convert_input_user(input_user):
    facebook_user_link = input_user.split('.')
    facebook_user_link[0] = 'https://mbasic'
    facebook_user_link = ('.').join(facebook_user_link)

    input_user = input_user.split('/')[-1].replace('\n','')
    return facebook_user_link, input_user


def convert_year(date):
    try:
        year = datetime.strptime(date, 'Yesterday at %H:%M %p').year
    except ValueError:
        try:
            year = datetime.strptime(date,'%B %d, %Y at %H:%M %p').year
        except ValueError:
            try:
                year = datetime.strptime(date,'%B %d at %H:%M %p').year    
            except ValueError:
                try: 
                    year = datetime.strptime(date,'%B %d, %Y').year
                except ValueError:
                    try:
                        year = datetime.strptime(date,'%B %Y').year
                    except ValueError:
                        year = datetime.strptime(date,'%Y').year
    return year


def get_all_years(driver, link):
    # Get every clickable years in 1 page
    years = [t.text for t in driver.find_elements_by_xpath("//div[@class='i']/a[not(contains(text(),'Show more'))]")]

    all_years = {}
    all_years = defaultdict(lambda:False, all_years)

    [all_years[y] for y in years]

    return all_years


def get_year_jump(all_years, current_year):
    all_years[current_year] = True
    for _, year in enumerate(all_years):
        if not all_years[year]:
            all_years[year] = True
            return year



def scrap_reaction(driver, xpath, element=None):
    try:
        if element:
            reaction = element.find_element_by_xpath(xpath)
        else:
            reaction = driver.find_element_by_xpath(xpath)

        current_time_url = driver.current_url
        driver.get(reaction.get_attribute("href"))
        time.sleep(DELAY_TIME)

        reaction_num = [e.text for e in driver.find_elements_by_xpath("//a[@role='button']/span")]
        reaction_type = [e.get_attribute('alt') for e in driver.find_elements_by_xpath("//a[@role='button']/img")]
        reaction_dict = convert_reaction(reaction_num, reaction_type)

        driver.get(current_time_url)
        time.sleep(DELAY_TIME)

        return reaction_dict

    except NoSuchElementException:
        return {}


def scrap_comment(driver):
    current_time_url = driver.current_url
    comments = [e.get_attribute('href') for e in driver.find_elements_by_xpath("//a[contains(text(),'Reply')]")]
    count_cmt = 0
    comment = {}
    for c in comments:

        count_cmt += 1

        # go through reply section of each comment
        driver.get(c)
        time.sleep(DELAY_TIME)

        comment = Comment()

        # IMPROVE GET REPLYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
        # MORE REPLY THEN THAT!
        # get reply info
        replies = driver.find_elements_by_xpath("//div[div[h3]]")
        max_reply = len(replies)

        # COMMENT INFORMATION
        info = replies[0].text.split('\n')
        comment.likes = scrap_reaction(driver, './/a[span[img]]', replies[0])

        if len(info) > 2:  # comment with TEXT
            comment.user = info[0]
            comment.content = info[1]
            comment.date = info[2].split(' · ')[-1]
            comment.reply = []
        else:  # comment with STICKER or GIF - NO TEXT
            comment.user = info[0]
            comment.date = info[1].split(' · ')[-1]
            comment.reply = []

        count_reply = 1
        while True:

            if count_reply == max_reply:
                break

            replies = driver.find_elements_by_xpath("//div[div[h3]]")

            reply = Reply()

            info = replies[count_reply].text.split('\n')
            reply.likes = scrap_reaction(driver, './/a[span[img]]', replies[count_reply])

            if len(info) > 2:
                reply.user = info[0]
                reply.content = info[1]
                reply.date = info[2].split(' · ')[-1]
            else: 
                reply.user = info[0]
                reply.content = info[1]
                reply.date = info[1].split(' · ')[-1]

            comment.reply.append(reply)

            count_reply += 1

        if count_cmt == MAX_CMT:
            break

    # back to post, go to next reply section of next comment
    driver.get(current_time_url)
    time.sleep(DELAY_TIME)
    
    return comment


def scrap_post(driver, p, scrap_cmt):
    """ Crawl all possible comments in post"""
    driver.get(p)
    time.sleep(DELAY_TIME)
    current_time_url = driver.current_url

    try:
        post = Post()
        post.url = p
        
        try:
            post.user = driver.find_element_by_xpath("//h3[@class='be bf bg bh']").text
        except NoSuchElementException:
            try:
                post.user = driver.find_element_by_xpath("//*[@class='actor']").text
            except NoSuchElementException:
                try:
                    post.user = driver.find_element_by_xpath("//h3[@class='bh bi bj bk']").text
                except NoSuchElementException:
                    print('\n[{}]\n[scrap_post] Error user name {}'.format(datetime.now().strftime("%m%d_%H%M%S"), sys.exc_info()))
                    print("Error at {}\n".format(post.url))
                

        post.date = driver.find_element_by_xpath("//abbr").text
        post.likes = scrap_reaction(driver, '//a[div[span[span[img[@alt="Like"]]]]]')
        
        content = [e.text for e in driver.find_elements_by_xpath("//div[@data-ft='{\"tn\":\"*s\"}']")]
        if len(content) == 0:
            content = [e.text for e in driver.find_elements_by_xpath("//div[@class='_2vj8']")]
        post.content = content

        if len(content) != 0:
            [[post.hashtag.append(h[1:]) for h in R.findall(c)] for c in content]

    except NoSuchElementException:
        print('\n[{}]\n[scrap_post] Error overall {}'.format(datetime.now().strftime("%m%d_%H%M%S"), sys.exc_info()))
        print("Error at {}\n".format(post.url))
        return Post()  

    if scrap_cmt is not None:
        comment = scrap_comment(driver)
        post.comment.append(comment)

    return post


def scrap_profile(driver, user, input_user, max_post=None, scrap_cmt=None):
    """ Crawl user information """
    driver.get(user)
    time.sleep(DELAY_TIME)

    # Catch every bugs
    list_post = []
    count_post = 0
    try:

        print("\n[{}]\nGo through Timeline...".format(datetime.now().strftime("%m%d_%H%M%S"), sys.exc_info()))
        try:
            driver.find_element_by_xpath("//a[contains(text(), 'Timeline')]").click()
        except NoSuchElementException:
            pass

        # Get all possible years
        all_years = get_all_years(driver, driver.current_url)

        screen_dir = os.path.join(SCREEN_DIR,input_user+'.png')
        print(screen_dir)
        driver.save_screenshot(screen_dir)

        while True:
            current_time_url = driver.current_url
            posts = [e.get_attribute('href') for e in driver.find_elements_by_xpath("//a[contains(text(), 'Full Story')]")]
            if len(posts) > 0:
                print('Batch from {}\n'.format(current_time_url))

                # Go through each post
                for p in posts:
                    # Counting post
                    count_post += 1

                    # Scrap
                    post = scrap_post(driver, p, scrap_cmt)
                    list_post.append(post)

                    # Reached maximum
                    if (max_post is not None) and (count_post >= max_post):
                        print("Reached to maximum posts per user")
                        print('Total: {} posts'.format(count_post))
                        save_json(list_post, input_user)
                        return

                # Go back to current timeline
                driver.get(current_time_url)
                time.sleep(DELAY_TIME)

                # Go to next timeline
                try:
                    show_more = driver.find_element_by_xpath("//a[span[contains(text(),'See More Stories')]]")
                    show_more.click()
                except NoSuchElementException:
                    try:
                        show_more = driver.find_element_by_xpath("//a[contains(text(), 'Show more')]")
                        show_more.click()
                    except NoSuchElementException:
                        # For no "Show More" case, need to find the post's year.
                        # Get the current crawled year, and choose the next year.
                        # E.g: Current post year is 2018, jump to 2017 so continute the crawling.
                        try:
                            # Find last post's date in batch, it will be the last spot in returned list
                            date = driver.find_elements_by_xpath('//abbr')[-1].text
                            # Use datetime to convert string to time format and get YEAR
                            # E.g: July 12, 2018 at 1:08 PM
                            # E.g: January 2004 
                            # E.g: December 13, 2009
                            current_year = convert_year(date)


                            # Find the year to jump. At case that:
                            year_jump = get_year_jump(all_years, str(current_year))

                            while True:
                                print("Jumping to year {}".format(year_jump))

                                # Find year button
                                show_more = driver.find_elements_by_xpath("//div/a[contains(text(), {})]".format(year_jump))

                                if len(show_more) != 0:
                                    show_more[0].click()
                                    break 

                                year_jump -= 1

                                # Set lower bounch 
                                if year_jump < 1990:
                                    raise NoSuchElementException

                        except NoSuchElementException:
                            print("There is no post to crawl")
                            break
                except IndexError:
                    print("Index error at link: {}".format(current_url))

                # Save every batch
                save_json(list_post, input_user)
            
            else:
                print("There is no post to crawl")
                break


        print('Total: {} posts'.format(count_post)) 
        save_json(list_post, input_user)

    except:
        print('ERROR: {}\nUser: {}\n'.format(sys.exc_info(), user))
        save_json(list_post, input_user)
        return
    


def start_driver():

    # global driver

    options = Options()
    options.add_argument("--disable-notification")
    options.add_argument("--disable-infobars")
    options.add_argument("--mute-audio")
    options.add_argument("headless")

    driver = webdriver.Chrome(options=options)

    return driver


def login(driver, email, password):
    """ Logging into our own profile """

    try:
        driver.get('https://mbasic.facebook.com')
        time.sleep(DELAY_TIME)

        driver.find_element_by_name('email').send_keys(email)
        driver.find_element_by_name('pass').send_keys(password)
        driver.find_element_by_name('login').click()

        # deal with "Not Now" button if it show off at first time
        not_now_button = driver.find_element_by_xpath("//a")
        if not_now_button.size != 0:
            not_now_button.click()

    except Exception as e:
        print('Error in Login')
        print(e)
        exit()


def main(data, log_file):

    # Init
    driver = start_driver()
    sys.stdout = open(log_file, 'w', encoding='utf-8')

    # Sign in information
    email = 'vinhvo5520@gmail.com'
    password = 'v0ducvinh'
    login(driver, email, password)

    # Travel
    for _, page in data.iterrows():
        facebook_user_link, input_user = convert_input_user(page['link'])
        print('Starting Scraping...')
        scrap_profile(driver, facebook_user_link, input_user, MAX_POST, SCRAP_CMT)

    # Close driver
    print("DONE !")
    driver.close()
    sys.stdout.close()
    

def load_data(input_dir):
    return pd.read_csv(input_dir)

def test(data, logs):
    print(data.iloc[:5])
    print(logs)

if __name__ == '__main__':
    INPUT_DIR = '../inputs/verified_page_3.csv'

    parser = argparse.ArgumentParser()
    parser.add_argument('start')
    parser.add_argument('log')
    parser.add_argument('batch')
    args = parser.parse_args()
 
    data_per_batch = int(args.batch)
    data = load_data(INPUT_DIR)
    input_data = data[int(args.start):int(args.start)+data_per_batch]
    main(input_data, args.log)
