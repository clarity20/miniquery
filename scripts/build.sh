case $OSTYPE in
  *android*)
    # First "make clean"
    rm -f mini.c mini

    # Generate C source from python
    cython -3 --embed mini.py

    # Generate EXE from C source file
    arm-linux-androideabi-clang -I /data/data/com.termux/files/usr/include/python3.7m -L /data/data/com.termux/files/usr/lib -o mini mini.c -lpython3.7m
    break
    ;;
  *linux*)
    echo "Linux not implemented."
    break
    ;;
  *win*)
    echo "Windows not implemented."
    break
    ;;
esac
