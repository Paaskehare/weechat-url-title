Weechat URL Title
=========================

This is a [WeeChat](http://pinboard.in) python script which will print out the title for any url that is printed in a buffer. It will also print the category for YouTube (e.g. "Music").

It will also (atleast try to) disregard popular media types to avoid downloading files and images.

Required
-----
For YouTube category support, json is required, it is default in **python => 2.6**
For older versions of python, you can use **simplejson**

Install
-----
Drop `url_title.py` in your weechat's python folder: `~/.weechat/python/`

Type `/python load url_title.py` to load, or put it in `~/.weechat/python/autostart` to have it start when you open weechat

To do
-----
* Add options for colouring
* Add option for custom prefix
* Add option to define ignored channels
* Add option to define channels which should always be fetched
* Add support for private messages
* Dont look for titles within the first few seconds of openening weechat (to avoid capturing urls from logs and when using BNC that has backbuffer)
