import time
import functools
import json
import sys
from statistics import mean
from parser_utils import Parser, NoQuestionFound, AAID_REGEX, FIND_DIGIT_REGEX

global feedback, tsl, resp
resp= None
feedback=[]
tsl= 1

class NoMethord(Exception):
    pass

def catch(func):
    @functools.wraps(func)
    def stub(self, *args, **kwargs):
        global feedback, resp
        try:
            return func(self, *args, *kwargs)
        except NoQuestionFound:  
            return True, True, feedback, None
        except NoMethord as e:
            
            return None, e, feedback, resp
        except KeyboardInterrupt:
            sys.exit()  
        except BaseException as e:
            return None, e, feedback, None
       
            
    return stub


class AnswerHandler:

    """
    handles all the answer logic
    """

    def __init__(self, session):
        self.sesh = session
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                                      ' Chrome/71.0.3578.98 Safari/537.36'}
        self.process_ans_url = 'https://www.drfrostmaths.com/process-answer-new.php'
        self.process_skip_url = 'https://www.drfrostmaths.com/process-skipquestion2.php'




    @catch
    def answer_questions_V2(self, url: str, auto_submit=True, tsl2=1, adm=False):
        feedback=[]
        try:
            aaid = FIND_DIGIT_REGEX.findall(AAID_REGEX.findall(url)[0])[0]
            print(aaid)
        except IndexError:
            raise InvalidURLException(url)

        while True:  # main loop
            
            url = "".join(url.split("&qnum=")[:1])
            try:
                url = url + "&qnum=" + data['qnum']
            except:
                url = url + "&qnum=" + '1'
            page = self.sesh.get(url, headers=self.headers).text 
            data, type_ = Parser.parse(page)  
            
            answer = self.find_answer(data, type_)  
            
            data['aaid'] = aaid
            
            self.new_type(answer, type_) 

            data = dict(data)
            del data['qid']
            data['qnum'] = str(int(data['qnum']) + 1)


             
    def find_answer(self, data: dict, type_: str):
        """
        Attempts to find the correct answer to the current question.

        :param data: request payload
        :param type_: answer type
        :return: correct answer string
        """
        data = dict(data)
        data[f'{type_}-answer-1'] = '1'  
        temp = str(f'Question number: {data["qnum"]}'+ ' | ' + f'Question type: {type_}')
        
        feedback.append(temp)

        r = self.sesh.post(self.process_ans_url, data=data, headers=self.headers)
       
        _json = json.loads(r.text)
        
        return _json['answer']  

    def submit(self, data: dict):
        
        try:
            r = self.sesh.post(self.process_ans_url, data=data, timeout=3)
        except BaseException:
            return False

        _json = json.loads(r.text)
        if not _json['isCorrect']:
            self.wrong_answer(_json, data)
            return False
        return True

    @staticmethod
    def new_type(answer: dict, type_: str):
        
        temp = str('<br/>' +  str(answer) +'<br/><br/>')
        feedback.append(temp)
        
        


    @staticmethod
    def wrong_answer(response, data: dict):
        print('-- Something Went Very Wrong --')
        print('The following data if for debugging:')
        print(f'Request: {data}')
        print(f'Response: {response}')