# encoding: utf-8

#
# Copyright (c) 2009 by ole <ole@ole.im>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Print titles for URLs, only in the active buffer
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2011-09-14, ole <ole@ole.im>
#     version 0.3-dev: fixed unicode encode error
# 2011-09-11, ole <ole@ole.im>
#     version 0.2-dev: add youtube support
# 2011-09-09, ole <ole@ole.im>
#     version 0.1-dev: dev snapshot
#

ENABLE_YOUTUBE = True

import weechat as w
import re
try:
  import json
except ImportError:
  # Import used for Python versions prior to 2.6
  # *** You will have to download and install simplejson for this to work.
  try:
    import simplejson as json
  except ImportError:
    # if we can't get this either, don't read YouTube category from gdata.youtube.com
    ENABLE_YOUTUBE = False
    
from HTMLParser import HTMLParser
from urllib2 import urlopen

SCRIPT_NAME = 'url_title'
SCRIPT_AUTHOR  = "Ole Bergmann <ole@ole.im>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Output URL Titles written in any channel"

DEFAULT_ENCODING = 'utf-8'

# colors, we dont want to screw up people's themes
COLOR_RESET = w.color('reset')
COLOR_TITLE = w.color("*default")
COLOR_LINK  = w.color('default')

# empty array which will be filled with urls to check
URLS = {}

# RegEx pattern to match urls
RE_URL = re.compile(r'(((http|ftp|https):\/\/|www\.)[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)')

# RegEx pattern to match title attribute of page
RE_TITLE = re.compile(r'<title.*>(.*?)<\/title>', re.I | re.S)

# RegEx pattern to match popular file extensions that should NOT be checked
RE_FILES = re.compile(r'.*(png|jpg|bmp|gif|avi|mpg|flv|3gp|mp4|exe|msi|mp3|flac|tar\.gz|tar\.bz2)$', re.I)

# RegEx used to match YouTube links
RE_YOUTUBE = re.compile('http://(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9\-_]{10,13})', re.I)

'''
 This function attempts to retrieve the title from given page content
'''

def youtube_title(page):

  # parse json
  entry = json.loads(page.decode(DEFAULT_ENCODING))['entry']
  # get category and video title
  vid = {'title': entry['title']['$t'], 'category': entry['media$group']['media$category'][0]['label']}

  # make sure the category is not bold formatted like the video title
  return '%s(%s)%s %s' % (COLOR_RESET, vid['category'], COLOR_TITLE, vid['title'])

def url_title(page):

  try:
    # search the page for a <title> attribute
    match = RE_TITLE.search(page)

    if match:

      # remove any whitespace we encounter (e.g. newlines) and replace it with a single space
      title = ' '.join(match.groups(0)[0].decode(DEFAULT_ENCODING).split())

      # init html parser
      h = HTMLParser()

      # if we found a title, return the title html decoded.
      if title: return h.unescape(title)
      else: return ''
  except AttributeError:
    return ''

'''
  Really simple function for appending an url to the URLS array
'''

def url_append(url, buffer = ""):
  
  global URLS

  URLS[url] = buffer

'''
  I don't like to do this, but it is impossible to run a background process
  otherwise within a weechat script. 

  This is instead of delaying the message we parsed the url from
'''

def url_process(url, command, rc, stdout, stderr):

  global URLS

  # make sure title is set
  title = ""
  
  # get the buffer object from the URLS array
  try:
    buffer = URLS[url]
  except KeyError:
    # probably already looked this one up, so just exit.
    return w.WEECHAT_RC_OK
  except IndexError:
    # probably already looked this one up, so just exit.
    return w.WEECHAT_RC_OK

  # unfortunately, we have to check up on this again,
  # since hook_process doesn't let us pass more than one variable:

  if ENABLE_YOUTUBE:
    match_yt = re.match(RE_YOUTUBE, url)
    if match_yt:
      # read from stdout, pass it to url_title
      title = youtube_title(stdout)
  
  # Not a YouTube link.
  if not title:
    # read from stdout, pass it to url_title
    title = url_title(stdout)
  
  if title:
    w.prnt(buffer,
      "+++\t%s%s %s%s- %s" % \
      (
       COLOR_TITLE,
       title.encode(DEFAULT_ENCODING),
       COLOR_RESET,
       COLOR_LINK,
       url,
      )
    )
  del URLS[url]
  return w.WEECHAT_RC_OK

def message_parse(data, signal, signal_data):

  # the server (to check which buffer the message belongs to)
  server = signal.split(",")[0]

  splits = signal_data.split(":")

  # the channel (to check which buffer the message belongs to)
  try:
    channel = splits[1].split(" ")[-2]
  except IndexError:
    # Don't check url titles on other than channels:
    return w.WEECHAT_RC_OK

  # the actual message
  message = ':'.join(splits[2:])

  # get the buffer the message was posted in
  buffer = w.info_get("irc_buffer", "%s,%s" % (server, channel))

  # get the current buffer
  current_buffer = w.current_buffer()

  # we only check for urls in the current buffer, so see if they match:
  if buffer == current_buffer:

    # search the message for any urls
    match = RE_URL.search(message)

    if match:
      
      # Great! we found one!
      url = match.groups(0)[0]

      # We don't want to download files and pictures.
      if not RE_FILES.match(url):

        # Assume http protocol if url matched with only the www. portion
        if url[:len("www.")] == "www.":
          url = "http://" + url

      	# append the url to URLS to make sure it knows which buffer it belongs to. 
        url_append(url, buffer)

        # by default only read 4096 first bytes of a webpage, youtube needs the whole thing for valid json though
        readBytes = "4096"

        # default, changes if we match a youtube link.
        lookup_url = url

        # look for youtube link if json is available:

        if ENABLE_YOUTUBE:
          match_yt = re.match(RE_YOUTUBE, url)
          if match_yt:
            lookup_url = "http://gdata.youtube.com/feeds/videos/%s?alt=json" % match_yt.groups(0)[1]
            # make sure we read the ENTIRE feed
            readBytes = ""

        # Check for python2 bin on systems where python3 is default
        python2_bin = w.info_get("python2_bin", "") or "python"
        cmd = python2_bin + " -c \"from urllib2 import urlopen; print(urlopen('%s').read(%s))\"" % (lookup_url, readBytes)

        # Wait 15 seconds before killing the process
        w.hook_process(cmd, 15 * 1000, "url_process", url)

  return w.WEECHAT_RC_OK

# only run if the script is not imported from another source:
if __name__ == "__main__":

  # attempt to register the script to weechat
  if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):

    # hook messages from buffers
    w.hook_signal("*,irc_in_privmsg", "message_parse", "")
