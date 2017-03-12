sudo apt-get update
sudo apt-get -y install python python-pip python-psycopg2 golang-go
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" >> /etc/apt/sources.list.d/pgdg.list'
wget -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O - | sudo apt-key add -
sudo apt-get update 
sudo apt-get -y install postgresql postgresql-contrib

sudo su - postgres -c "createdb youstatdbb; psql template1 -c \"CREATE USER evex WITH PASSWORD 'throwaway2016'; GRANT ALL PRIVILEGES ON DATABASE youstatdbb to evex;\""
python manage.py migrate
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
