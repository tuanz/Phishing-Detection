#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author：Janet Chou
from sklearn.model_selection import train_test_split
from sklearn.externals import joblib
from sklearn import ensemble
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,classification_report,confusion_matrix
from sklearn.feature_selection import SelectKBest,SelectPercentile
from sklearn.feature_selection import chi2
import jieba
import re
from bs4 import BeautifulSoup
import os
import numpy as np
import codecs

np.set_printoptions(suppress=True)

# mainfile='./data/file_list_20170430_new的副本.txt'
# WebDirectory='./data/file的副本/'

#获得URLkeyword ；URLchar；action；title

def get_dic():
    URLKeyword, URLchar, action, title = [], [], {}, {}
    with open('./dict/P_url_key_list','r') as f1:
        for i in f1:
            URLKeyword.append(i.strip())
    with open('./dict/URL_keyword.txt','r') as f2:
        for j in f2:
            URLchar.append(j.strip().split(',')[0].lower())
    with open('./dict/unique_action.txt','r') as f3:
        for z in f3:
            action[z.strip()] = 0
    with open('./dict/unique_title.txt','r') as f4:
        for h in f4:
            title[h.strip()] = 0
    return URLKeyword, URLchar, action, title


def URL_feature(data, URLKeyword, URLchar):
    data = data.lower()
    # 钓鱼网站关键字特征（login，qrcode）
    URL_Pkey_list = [data.count(key) for key in URLKeyword]

    IPcheck = 0
    pattern = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    result = re.findall(pattern, data)
    if len(result)>0:
        IPcheck = 1

    http_result = 0
    if data.startswith('https://'):
        http_result = 1
        data = data[8:]
    elif data.startswith('http://'):
        data = data[7:]
    # 高频字母特征
    Char_Counts = [data.count(char) for char in URLchar]
    url_len = len(data)
    np_chars = np.asarray(Char_Counts)
    t1 = [np_chars.sum(), np_chars.max(), np_chars.std(), np_chars.mean(), sum(np_chars > 0)]
    num_chars_per = np_chars.sum() / float(url_len)
    t2 = np.asarray([IPcheck, http_result, url_len, num_chars_per] + Char_Counts)

    return np.hstack((t1, t2, np.asarray(URL_Pkey_list)))


def Web_feature(Web_data, title, action, MD5_list):
    P_Feature = [
        'alert',
        'register',
        'login',
        'qrcode',
        'javascript:alert_login('')'
    ]
    try:
        soup = BeautifulSoup(Web_data, "html.parser")
        # 关键词标签
        cf_count = [Web_data.count(cf) for cf in P_Feature]
        doc_length = len(Web_data)

        # ------- feature for p---------#
        inputs_h = soup.findAll('input', {'type': 'hidden'})
        inputs_b = soup.findAll('input', {'type': 'button'})
        buttons = soup.findAll('button')
        scripts = soup.findAll('script')
        imgs = soup.findAll('img')
        forms = soup.findAll('form', {'method': 'post'})

        scripts_len_list = [len(str(scr)) for scr in scripts]
        script_len = sum(scripts_len_list)
        script_len_per = script_len / float(doc_length)

        num_scripts = len(scripts)
        num_h_inputs = len(inputs_h)
        num_b_inputs = len(inputs_b)
        num_btns = len(buttons)
        num_img = len(imgs)
        num_forms = len(forms)

        p_t_list = [0] * (len(title.keys()) + 1)
        p_f_list = [0] * (len(action.keys()) + 1)

        if soup.title:
            t_title = soup.title.string
            if t_title:
                t_seg = jieba.cut(t_title)
                for seg in t_seg:
                    key_index = title.get(seg, -1)
                    p_t_list[key_index] += 1

        t1 = np.asarray(p_t_list)
        t_np = np.hstack((t1[:-1], [t1.sum(), t1.max(), t1.std(), t1.mean(), sum(t1 > 0)]))

        for i in forms:
            key_index = action.get(i.get('action'), -1)
            p_f_list[key_index] += 1

        t2 = np.asarray(p_f_list)
        f_np = np.hstack((t2[:-1], [t2.sum(), t2.max(), t2.std(), t2.mean(), sum(t2 > 0)]))

        other = np.asarray(
            [doc_length, script_len, script_len_per, num_scripts, num_h_inputs, num_b_inputs, num_btns, num_img,
             num_forms] + cf_count)
        return np.hstack((t_np, f_np, other))
    except:
        print("wrong")
        print(MD5_list)
        return np.asarray([0]*145)

def test_RandomForestClassifier(*data):
    '''
    测试 RandomForestClassifier 的用法

    :param data: 可变参数。它是一个元组，这里要求其元素依次为：训练样本集、测试样本集、训练样本的标记、测试样本的标记
    :return: None
    '''
    X_train,X_test,y_train,y_test=data
    clf=ensemble.RandomForestClassifier(bootstrap=True,criterion='gini',max_depth=50,n_estimators=142)
    clf.fit(X_train,y_train)
    y_pred = clf.predict(X_test)
    print("Traing Score:%f"%clf.score(X_train,y_train))
    print("Testing Score:%f"%clf.score(X_test,y_test))
    return y_pred, y_test

def feature_selection(X,Y):
    Selector = SelectKBest(chi2, k=153)
    Selector.fit(X,Y)
    return Selector.transform(X),Y,Selector.get_support(True)

def evaluate_model(y_true,y_pred):
    print('Accuracy Score(normalize=True):', accuracy_score(y_true, y_pred, normalize=True))
    # print('Precision Score:', precision_score(y_true, y_pred,pos_label=1))
    # print('Recall Score:', recall_score(y_true, y_pred,pos_label=1))
    # print('F1 Score:', f1_score(y_true, y_pred,pos_label=1))
    print('Classification Report:\n', classification_report(y_true, y_pred,labels=[0,1],target_names=["Normal Website", "Hidden Link Website"]))
    print('Confusion Matrix:\n', confusion_matrix(y_true, y_pred, labels=[0, 1]))
#遍历文件，获得MD5目录和标签y
def traverse_directory(WebDirectory,mainfile):
    MD5_list = list()
    flag_list = list()
    URL_list = list()
    with open(mainfile,'r') as f:
        for i in f:
            flag=i.split(',',4)[1]
            if flag=='n':
                flag_list.append(1)
                MD5 = i.split(',', 4)[2]
                each_file = os.path.join(WebDirectory, MD5)
                MD5_list.append(each_file)
                URL_list.append(i.strip().split(',',4)[3])
            elif flag=='p':
                flag_list.append(0)
                MD5 = i.split(',', 4)[2]
                each_file = os.path.join(WebDirectory, MD5)
                MD5_list.append(each_file)
                URL_list.append(i.strip().split(',', 4)[3])
    return MD5_list,flag_list,URL_list

def read_file(filename):
    try:
        f=codecs.open(filename,'r',encoding='utf-8')
        Web_data=f.readlines()
        # print(filename)
        # print('******')
        Web_data = '\n'.join(Web_data)
        f.close()
    except:
        f=codecs.open(filename,'r',encoding='gb18030')
        Web_data = f.readlines()
        # print(Web_data)
        # print(filename)
        # print('******')
        Web_data = '\n'.join(Web_data)
        f.close()
    return Web_data


def main():
    URLKeyword, URLchar, action, title = get_dic()

    """
    #load training dataset
    mainfile = './data/file_list_20170430_new的副本.txt'
    WebDirectory = './data/file的副本/'
    MD5_list, flag_list, URL_list = traverse_directory(WebDirectory, mainfile)
    X_train = list()
    Y_train = flag_list
    for i in range(len(MD5_list)):
        URL = URL_list[i]
        Web_data = read_file(MD5_list[i])
        web_vec = Web_feature(Web_data, title, action, MD5_list[i])
        URL_vec = URL_feature(URL, URLKeyword, URLchar)
        feature = np.hstack((web_vec, URL_vec))
        X_train.append(feature)
        # print(len(feature))
    print(len(X_train),len(Y_train))

    X_train = np.asarray(X_train)
    Y_train = np.asarray(Y_train)

    #feature selection
    X_train, Y_train, F_index= feature_selection(X_train, Y_train)
    print(F_index)


    #split dataset
    X_train, X_test, y_train, y_test = train_test_split(X_train, Y_train, test_size=0.25, random_state=0, stratify=Y_train)
    #train model
    clf = ensemble.RandomForestClassifier(bootstrap=True, criterion='gini', max_depth=50, n_estimators=142)
    clf.fit(X_train, y_train)
    joblib.dump(clf,'RF_model.m')
    print("Traing Score:%f" % clf.score(X_train, y_train))
    # print("Testing Score:%f"%clf.score(X_test,y_test))
    
    """

    F_index = [0, 96, 97, 101, 131, 132, 134, 137, 138, 140, 142, 143, 145, 149, 154, 157, 158, 161,
         162, 163, 165, 168, 171, 172, 173, 175, 176, 178, 179, 181, 184, 185, 194, 202, 206, 208,
         209, 210, 215, 226, 229, 230, 278, 280, 282, 283, 284, 285, 286, 287, 288, 289, 294, 295,
         296, 297, 298, 299, 301, 302, 306, 307, 308, 309, 310, 311, 312, 313, 315, 316, 318, 319,
         321, 322, 323, 324, 325, 327, 330, 331, 332, 333, 334, 337, 338, 339, 340, 343, 344, 345,
         346, 347, 348, 352, 354, 356, 357, 361, 363, 364, 366, 370, 373, 374, 376, 377, 378, 379,
         381, 383, 385, 386, 387, 388, 390, 393, 395, 396, 397, 398, 399, 400, 402, 403, 404, 405,
         406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 418, 421, 422, 424, 425, 426, 427,
         428, 429, 431, 432, 434, 435, 437, 439, 553]

    #load testing dataset
    RF_model = joblib.load('RF_model.m')
    mainfile1 = './data/file_list_10000.txt'
    WebDirectory1 = './data/file1/'
    MD5_list1, flag_list1, URL_list1 = traverse_directory(WebDirectory1, mainfile1)
    X_test = list()
    Y_test = flag_list1
    for h in range(len(MD5_list1)):
        s_fea = []
        URL1 = URL_list1[h]
        Web_data1 = read_file(MD5_list1[h])
        web_vec1 = Web_feature(Web_data1, title, action, MD5_list1[h])
        URL_vec1 = URL_feature(URL1, URLKeyword, URLchar)
        feature1 = np.hstack((web_vec1, URL_vec1))
        for j in F_index:
            s_fea.append(feature1[j])
        X_test.append(s_fea)
        # print("********")
    print(len(X_test),len(Y_test))



    #testing model
    y_pred = RF_model.predict(X_test)
    print("Testing Score:%f" % RF_model.score(X_test, Y_test))
    evaluate_model(Y_test, y_pred)




if __name__=="__main__":
    main()