NAME = pygenda_clipboard

SRC = $(NAME).c
TARGET = lib$(NAME).so

INCLUDE_DIR = /usr/include

MACHINE = $(shell uname -m)

ifeq ($(MACHINE), x86_64)
	INCLUDE_PLATFORM_DIR = /usr/lib64
else ifeq ($(MACHINE), aarch64)
	INCLUDE_PLATFORM_DIR = /usr/lib/aarch64-linux-gnu
else
	INCLUDE_PLATFORM_DIR = /usr/lib
endif

CC_INCLUDE_DIRS = -I$(INCLUDE_DIR)/gtk-3.0 -I$(INCLUDE_DIR)/glib-2.0 -I$(INCLUDE_PLATFORM_DIR)/glib-2.0/include -I$(INCLUDE_DIR)/pango-1.0 -I$(INCLUDE_DIR)/harfbuzz -I$(INCLUDE_DIR)/cairo -I$(INCLUDE_DIR)/gdk-pixbuf-2.0 -I$(INCLUDE_DIR)/atk-1.0

# Targets...

$(TARGET): $(SRC)
	gcc $(CC_INCLUDE_DIRS) -shared -o $(TARGET) -fPIC $(SRC)
	strip $(TARGET)

cp: $(TARGET)
	cp $(TARGET) ../pygenda/

uninstall:
	rm -rf ../pygenda/$(TARGET)

clean:
	rm -rf $(TARGET)
