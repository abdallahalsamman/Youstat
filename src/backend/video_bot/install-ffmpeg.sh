git clone git://git.videolan.org/x264.git
git clone git://source.ffmpeg.org/ffmpeg.git
cd x264
./configure --enable-static --enable-shared
make -j8
sudo make install
cd ../ffmpeg
./configure --enable-gpl --enable-nonfree --enable-pthreads --enable-libx264
make -j8
sudo make install
