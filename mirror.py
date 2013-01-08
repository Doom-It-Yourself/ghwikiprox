#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2012 Kasper Menten
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__='Kasper Menten (kasper.menten@gmx.com)'

# This code is a reduction / adaptation of mirrorrr project 
# (http://code.google.com/p/mirrorrr/ by Brett Slatkin) 
# held specifically to achieve the goals to build a proxy for a wiki in an 
# account published at github. 
# If you want a full proxy to run on GAE, use the mirrorr.

# Set up your github user/repo here:
GITHUB_USER = 'Doom-It-Yourself/doomityourself'

GITHUB_PREFIX ='/github.com/'
GITHUB_SUFFIX ='/wiki/'
DEBUG = False
HTTP_PREFIX = "http://"
IGNORE_HEADERS = frozenset([
  'set-cookie',
  'expires',
  'cache-control',
  # Ignore hop-by-hop headers
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
])

import logging
import wsgiref.handlers

from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.runtime import apiproxy_errors

class MirroredContent(object):
  def __init__(self, original_address, translated_address,
               status, headers, data, base_url):
    self.original_address = original_address
    self.translated_address = translated_address
    self.status = status
    self.headers = headers
    self.data = data
    self.base_url = base_url

  @staticmethod
  def fetch_and_store(base_url, translated_address, mirrored_url):
    """Fetch a page.
    
    Args:
      base_url: The hostname of the page that's being mirrored.
      translated_address: The URL of the mirrored page on this site.
      mirrored_url: The URL of the original page. Hostname should match
        the base_url.
    
    Returns:
      A new MirroredContent object, if the page was successfully retrieved.
      None if any errors occurred or the content could not be retrieved.
    """
    logging.debug("Fetching '%s'", mirrored_url)
    try:
      response = urlfetch.fetch(mirrored_url)
    except (urlfetch.Error, apiproxy_errors.Error):
      logging.exception("Could not fetch URL")
      return None

    adjusted_headers = {}
    for key, value in response.headers.iteritems():
      adjusted_key = key.lower()
      if adjusted_key not in IGNORE_HEADERS:
        adjusted_headers[adjusted_key] = value

    return MirroredContent(
      base_url=base_url,
      original_address=mirrored_url,
      translated_address=translated_address,
      status=response.status_code,
      headers=adjusted_headers,
      data=response.content)
      

class MirrorHandler(webapp.RequestHandler):
  def get_relative_url(self):
    slash = self.request.url.find("/", len(self.request.scheme + "://"))
    if slash == -1:
      return "/"
    return GITHUB_PREFIX + GITHUB_USER + GITHUB_SUFFIX + self.request.url[slash:]

  def get(self, base_url):
    assert base_url
    logging.debug('User-Agent = "%s", Referrer = "%s"',
                  self.request.user_agent,
                  self.request.referer)
    logging.debug('Base_url = "%s", url = "%s"', base_url, self.request.url)
    translated_address = self.get_relative_url()[1:]  # remove leading /
    content = MirroredContent.fetch_and_store(base_url, translated_address, 
      HTTP_PREFIX + translated_address)
    if content is None:
      return self.error(404)
    for key, value in content.headers.iteritems():
      self.response.headers[key] = value
    self.response.out.write(content.data)


app = webapp.WSGIApplication([
  (r"/", MirrorHandler),
  (r"/([^/]+).*", MirrorHandler)
], debug=DEBUG)


def main():
  wsgiref.handlers.CGIHandler().run(app)


if __name__ == "__main__":
  main()
