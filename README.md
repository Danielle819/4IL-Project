**About the Project**: 4IL is an online game of Four in a Line, in which you can create a user, score points, add friends, and most importantly - play with other people in your local network. 

**System capabilities**:  - Creating a user
                      - Creating an open game room/ID game room
                      - Joining an open game room/ID game room
                      - Inviting another player for a game
                      - Earning points by playing
                      - Getting the TOPTEN list of ten highest scorers in the game
                      - Adding friends, sending friend requests
                      - Receiving updates about friends, game invites, and TOPTEN list in real-time
                      

**Environment requirements**: Windows Environment, Python 3, and the following modules: sqlite3, numpy, PyQt5, cryptography, base64

**Server files**: server.py, commprot.py, game.py, as well as the 'sqlite' directory which is in the main directory

**Client files**: client.py, commprot.py, game.py, as well as the directories 'UIfiles' and 'pictures' in the main directory


**Server-side**: To use the system, the server needs to be up and running on the local network.
                Make sure your environment matches the requirements in **Environment requirements** and download the files detailed in **Server files**.
                Then run 'server.py'. The server itself is not for the client's use and only enables the client's functionalities.
                Note that data is stored locally on the machine hosting the server, so either the server should be running only on a specific machine in the LAN,
                or transfer the updated 'sqlite' directory to the next hosting machine.

**Client-side**: Note that in order to use the system, the server needs to be up and running on the local network.
                To enter the game, make sure your environment matches the requirements in **Environment requirements** and download the files detailed in **Client files**.
                Simply run 'client.py' and all of the game's functionalities will be available.
            
