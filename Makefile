CC = gcc
CFLAGS = -std=c99 -Wall -Wextra -O2 -fPIC -I.
LDFLAGS = -shared

TARGET_LIB = libswuir_il.so
TARGET_POC = swuir_poc
IL_SRC = swuir_il.c
POC_SRC = swuir.c

all: $(TARGET_LIB) $(TARGET_POC)

$(TARGET_LIB): $(IL_SRC) swuir_il.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(TARGET_LIB) $(IL_SRC)

$(TARGET_POC): $(POC_SRC)
	$(CC) $(CFLAGS) -o $(TARGET_POC) $(POC_SRC) -lpthread

install: $(TARGET_LIB)
	cp $(TARGET_LIB) /usr/local/lib/
	ldconfig

clean:
	rm -f $(TARGET_LIB) $(TARGET_POC)

test: $(TARGET_LIB) $(TARGET_POC)
	./$(TARGET_POC)
	python3 python_bindings/swuir_il.py

.PHONY: all install clean test