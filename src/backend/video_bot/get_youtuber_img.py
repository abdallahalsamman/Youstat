from bs4 import BeautifulSoup
import requests
import re
import urllib2
import os, sys
import cookielib
import json

def get_soup(url,header):
    return BeautifulSoup(urllib2.urlopen(urllib2.Request(url,headers=header)),'html.parser')


query = sys.argv[1]# you can change the query for the image  here
image_type="ActiOn"
query= query.split()
query='+'.join(query)
url="https://www.google.co.in/search?q="+query+"&source=lnms&tbm=isch"

#add the directory for your image here
DIR="Pictures/"
if not os.path.exists(DIR):
            os.mkdir(DIR)

DIR = os.path.join(DIR, query.split()[0])

if not os.path.exists(DIR):
            os.mkdir(DIR)
print url

header={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"
}
soup = get_soup(url,header)


ActualImages=[]# contains the link for Large original images, type of  image
for a in soup.find_all("div",{"class":"rg_meta"}):
    link , Type =json.loads(a.text)["ou"]  ,json.loads(a.text)["ity"]
    ActualImages.append((link,Type))

print  "there are total" , len(ActualImages),"images"


###print images
for i , (img , Type) in enumerate( ActualImages):
    try:
        cntr = len(os.listdir(DIR)) + 1
        if cntr >= 20:
            break
        req = urllib2.Request(img, headers={'User-Agent' : header})
        raw_img = urllib2.urlopen(req, timeout=4).read()


        print cntr
        if len(Type)==0:
            f = open(os.path.join(DIR , str(cntr)+".jpg"), 'wb')
        else :
            f = open(os.path.join(DIR , str(cntr)+"."+Type), 'wb')


        f.write(raw_img)
        f.close()
    except Exception as e:
        print "could not load : "+img
        print e