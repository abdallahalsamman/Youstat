sudo apt-get update
sudo apt-get -y install python python-pip
sudo apt-get -y install golang-go

# fix python locale problem
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
sudo dpkg-reconfigure locales

sudo pip install -r requirements.txt
git clone https://github.com/direnv/direnv
cd direnv
sudo make install
cd ..
rm -rf direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
