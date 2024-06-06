""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Websocket Manager Class
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from http.cookies import SimpleCookie
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.consumer import SyncConsumer

from Backend.authentication import ValidateAuthToken

class BaseWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.scope["authorization"] = False
        if not "headers" in self.scope:
            raise Exception("Headers not found")
        
        cookies = SimpleCookie()
        for name, value in self.scope["headers"]:
            if name == b"cookie":
                cookies.load(rawdata=value.decode("utf-8"))
                break
        self.scope["cookies"] = cookies = {k: v.value for k, v in cookies.items()}

        self.scope["user"] = None
        if "accessToken" in self.scope["cookies"].keys():
            user = ValidateAuthToken(self.scope["cookies"]["accessToken"])
            self.scope["user"] = user

        if self.scope["user"]:
            await self.accept()
        else:
            await self.close()

