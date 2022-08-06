# Oink (a local network messaging app)

Oink is a desktop messaging app for the local network. It uses sockets to find other Oink clients on the local network and send them messages. There is no persistence--message and contact data is not saved when the app is shut down. 

# Disclaimer

This project is very much a proof-of-concept--it's not ready to be seriously used. You're welcome to try it out, but it's still very unpolished. Here are some things to be aware of:

### Security

Oink needs an open port on your machine to work, and there is very ugly Python code listening for and processing any data that comes over that port. So I definitely would not use this on any public or untrusted network. 

### Firewall rules

Following on the above point, some machines (I saw this on Windows 11) may have security policies that disallow direct access to ports. So you may have to allow Oink through your firewall to use it. 

### Network traffic

To find other Oink clients on the network automatically, Oink sends out "scan" packets. By default, these packets are sent to every other host on the local network (Oink assumes a class C network, so it pings 255 IP addresses). It does this scan every 5 seconds. 

# Installation

If you still want to try it out, installation should be straightforward. Just clone the repo and run oink.py.

Note that there is a 'USE_LOCALHOST' option in config.py--if you set that to True, Oink will run entirely within your machine without exposing any external ports. That option will pick a random localhost IP, so you can start Oink multiple times to test out the messaging options.