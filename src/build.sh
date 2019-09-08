case $OSTYPE in:
  *android*)
    # First "make clean"
    rm -f includes.pyx  includes.c  build/temp.linux-armv7l-3.7/includes.o  includes.cpython-37m.so

    # Auto-generate includes.pyx, the list of python files to be included in the DLL
    for fn in *.py; do
      if [[ ! "$fn" =~ ^(setup|include)\.py ]]; then
        echo include \"$fn\" >> includes.pyx
      fi
    done

    # Convert the list into a C source file
    cython -3 includes.pyx

    # Convert C source into .o object file
    arm-linux-androideabi-clang -mfloat-abi=softfp -mfpu=vfpv3-d16 -Wno-unused-result -Wsign-compare -Wunreachable-code -DNDEBUG -g -fwrapv -O3 -Wall -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -march=armv7-a -mfpu=neon -mfloat-abi=softfp -mthumb -Os -fPIC -I/data/data/com.termux/files/usr/include/python3.7m -c includes.c -o build/temp.linux-armv7l-3.7/includes.o

    # Generate DLL/.so from object file
    arm-linux-androideabi-clang -shared -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib -march=armv7-a -Wl,--fix-cortex-a8 -L/data/data/com.termux/files/usr/lib -march=armv7-a -landroid-support -L/home/builder/.termux-build/_cache/android5-19b-arm-21-v3/sysroot/usr/lib build/temp.linux-armv7l-3.7/includes.o -L/data/data/com.termux/files/usr/lib -lpython3.7m -o /data/data/com.termux/files/home/projects/miniquery/src/includes.cpython-37m.so
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
