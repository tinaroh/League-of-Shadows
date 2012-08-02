﻿#!/usr/bin/env python

import os
from random import shuffle

from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.api import users, mail
from google.appengine.ext import webapp
from models import *

class Renderer(webapp.RequestHandler):
  def get_mission(self, assassin, victim, status=None, timestamp=None):
    mission = Mission()
    mission.assassin = assassin
    mission.victim = victim
    mission.status = status
    mission.timestamp = timestamp
    return mission

  def get(self):
    game_name = 'TEST'
    player_name = users.get_current_user().nickname()

    # Game statistics
    stats_list = []
    stats_list.append(('Total Players', 5))
    stats_list.append(('Players Dead', 3))
    stats_list.append(('Your Kills', 2))

    # Typical URL combination
    # admin/render?registered=false&started=false
    # admin/render?registered=false&started=true
    # admin/render?registered=true&started=false
    # admin/render?registered=true&started=true
    # admin/render?registered=true&started=true&player=killed
    # admin/render?registered=true&started=true&player=suicide
    # admin/render?registered=true&started=true&over=true

    is_registered = self.request.get('registered') or self.request.get('is_registered')
    game_started = self.request.get('started') or self.request.get('game_started')
    is_suicide = False
    death_mission = None
    target_mission = None
    winner = None
    player_code = 'CODE'

    if self.request.get('over'):
      winner = self.get_mission('winner', 'winner', 9001)

    if self.request.get('player') == 'killed':
      death_mission = self.get_mission('assassin', player_name)
    elif self.request.get('player') == 'suicide':
      is_suicide = True
    else:
      target_mission = self.get_mission(player_name, 'victim')

    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'

    template_values = {
      'csrf_token': 'XXX',
      'game_name': game_name,
      'game_started': game_started,
      'games': None,
      'is_registered': is_registered,
      'is_suicide': is_suicide,
      'killcode_quips': [
          "Remember it, and surrender it upon death.",
          "Hover to view. Keep it hidden. Keep it safe."
      ],
      'num_players': 5,
      'target_mission': target_mission,
      'death_mission': death_mission,
      'stats_list': stats_list,
      'stats_list_width': len(stats_list) * 120,
      'url': url,
      'url_linktext': url_linktext,
      'player_name': player_name,
      'player_code': player_code,
      'winner': winner,
      'FLAGS_show_game_title': os.environ['show_game_title'] == "True",
      'FLAGS_max_players': int(os.environ['max_players'])
    }

    path = os.path.join(os.path.dirname(__file__)+ '/../templates/', 'index.html')
    self.response.out.write(template.render(path, template_values))

class CreateGame(webapp.RequestHandler):
  def get(self):
    game_name = self.request.get('game_name')
    if db.get(game_key(game_name or 'default_game')):
      self.response.out.write("Exists")
      return
    game = Game(key_name=game_name or 'default_game')
    game.put()
    self.response.out.write("Created")
	
class EndGame(webapp.RequestHandler):
  def get(self):
    game_name = self.request.get('game_name')
    missions = Mission.in_game(game_name).fetch(None)
    db.delete(missions)
    self.response.out.write("Done")

class StartGame(webapp.RequestHandler):
  def get(self):
    game_name = self.request.get('game_name')
    if Game.has_started(game_name):
      self.response.out.write("Already started")
      return

    users = Player.in_game(game_name).fetch(None)
    shuffle(users)

    assassin = users[len(users) - 1]
    for user in users:
      mission = Mission(parent=game_key(game_name))
      mission.assassin = assassin.nickname
      mission.victim = user.nickname
      mission.put()
      assassin = user
      # Send email to all players
      if not mail.is_email_valid(user.email):
        self.response.out.write("Warning: Invalid email: " + user.email)
      else:
        sender_address = "League of Interns <billycao@google.com>"
        subject = "[League of Interns] Let the games begin!"
        body = """
Thanks for joining the League of Interns!

The games have begun!

Check the site for your first target, updated rules/FAQ, and your kill code (remember it!).

If you haven't yet, pick up your weapon from MTV-43-132!

---

Important note: The boat cruise tonight is fair game for all. Indoors/outdoors no one is safe on the boat!

Also remember that otherwise the no indoors rule is strict. This includes indoor cafes.

An extra note: The two planners with database access (billycao@ and nsolichin@) have chosen to exempt ourselves from being able to win prizes in the interest of fairness. We'll still play, we just cant win.

We'll only tamper with the database if something goes wrong and manual editing is required.

Be ninja, play fair, and good luck!

---

This message was automatically generated by League of Interns. Problems? Let us know!

Don't worry, we won't spam you. Future email notifications will be opt-out.
"""
        html = """
Thanks for joining the <a href="https://leagueofinterns.googleplex.com/?game_name=%s">League of Interns</a>!<br />
<br />
<b>The games have begun</b>!<br />
<br />
Check the site for your first target, updated rules/FAQ, and your kill code (remember it!).<br />
<br />
If you haven't yet, pick up your weapon from MTV-43-132!<br />
<br />
--- <br />
<br />
Important note: The boat cruise tonight is fair game for all. Indoors/outdoors no one is safe on the boat!<br />
<br />
Also remember that otherwise the no indoors rule is strict. This includes indoor cafes.<br />
<br />
An extra note: The two planners with database access (billycao@ and nsolichin@) have chosen to exempt ourselves from being able to win prizes in the interest of fairness. We'll still play, we just cant win.<br />We'll only tamper with the database if something goes wrong and manual editing is required.<br />
<br />
Be ninja, play fair, and <b>good luck</b>!<br />
---<br />
<br />
This message was automatically generated by League of Interns. Problems? Let us know!<br />
<br />
Don't worry, we won't spam you. Future email notifications will be opt-out.<br />
""" % game_name
        mail.send_mail(sender_address, user.email, subject, body, html=html)
    self.response.out.write("Done")
    
