######################################
# Makefile by CubeMX2Makefile.py
######################################

######################################
# target
######################################
APP_NAME= $APP_NAME

######################################
# building variables
######################################
# debug build?
DEBUG = 1
# optimization
OPT_LEVEL = O0
OPT = $$(OPT_LEVEL)


######################################
# source
######################################
$C_SOURCES
$ASM_SOURCES

#######################################
# binaries
#######################################
CC = arm-none-eabi-gcc
AS = arm-none-eabi-gcc
LD = arm-none-eabi-gcc
CP = arm-none-eabi-objcopy
AR = arm-none-eabi-ar
SZ = arm-none-eabi-size
HEX = $$(CP) -O ihex
BIN = $$(CP) -O binary -S


#######################################
# CFLAGS
#######################################
# macros for gcc
$AS_DEFS
$C_DEFS
# includes for gcc
$AS_INCLUDES
$C_INCLUDES
# compile gcc flags

C_INCLUDES += -I$GCC_PATH/arm-none-eabi/include

ASFLAGS = $MCU -mfloat-abi=$FLOAT_ABI $$(AS_DEFS) $$(AS_INCLUDES) $$(OPT) -Wall 
CFLAGS = $MCU -mfloat-abi=$FLOAT_ABI $$(C_DEFS) $$(C_INCLUDES) -$$(OPT) 
CFLAGS += -g3 -Wall -ffunction-sections -c -fmessage-length=0 -Wno-unused-variable -Wno-pointer-sign -mthumb -specs=nosys.specs 
CFLAGS += -Wno-main -Wno-format -Wno-address -Wno-unused-but-set-variable -Wno-strict-aliasing -Wno-parentheses -Wno-missing-braces
ifeq ($$(DEBUG), 1)
CFLAGS += -g -gdwarf-2
endif
# Generate dependency information
#CFLAGS += -std=c99 -MD -MP -MF .dep/$$(@F).d

#######################################
# LDFLAGS
#######################################
# link script
$LDSCRIPT
# libraries
LIBS = -lc -lm
LIBDIR = $LD_STD_LIBS $LD_LIB_DIRS


LDFLAGS=
LDFLAGS+= -mthumb $MCU -mfloat-abi=$FLOAT_ABI -specs=nosys.specs -Wl,-Map=output.map -Wl,--gc-sections

##############################################################################
# default action: build all
# primary TARGETS
COMP_VERSION=$$(shell $$(CC) -dumpversion)
TARGET=$$(APP_NAME)--opt=$$(OPT)--comp=$$(CC)--comp_version=$$(COMP_VERSION)


#######################################
# pathes
#######################################
# Build path
BUILD_DIR = .build/$$(TARGET)
BIN_DIR = bin

all: default 

default: $$(BIN_DIR) $$(BIN_DIR)/$$(TARGET).elf

FORCE :
#######################################
# build the application
#######################################
# list of ASM program objects
ASM_OBJECTS = $$(addprefix $$(BUILD_DIR)/,$$(notdir $$(ASM_SOURCES:.s=.o)))
vpath %.s $$(sort $$(dir $$(ASM_SOURCES)))

# list of objects
OBJECTS += $$(addprefix $$(BUILD_DIR)/,$$(notdir $$(C_SOURCES:.c=.o)))
vpath %.c $$(sort $$(dir $$(C_SOURCES)))


###############################################


$$(BUILD_DIR)/%.o: %.c Makefile | $$(BUILD_DIR)
	@echo Compiling:  $$<
	@$$(CC) -c $$(CFLAGS) $$< -o $$@

$$(BUILD_DIR)/%.o: %.s Makefile | $$(BUILD_DIR)
	@echo Assembling: $$<
	@$$(AS) -c $$(CFLAGS) $$< -o $$@

$$(BIN_DIR)/$$(TARGET).elf: $$(ASM_OBJECTS) $$(OBJECTS) Makefile
	$$(LD) $$(ASM_OBJECTS) $$(OBJECTS)	$$(LDFLAGS) -T$$(LDSCRIPT) -o $$@ -g
	$$(SZ) $$@

$$(BUILD_DIR):
	mkdir -p $$@

$$(BIN_DIR):
	mkdir -p $$@


#######################################
# clean up
#######################################
clean:
	-rm -fR .dep $$(BUILD_DIR) $$(BIN_DIR)
	-rm -f *.dot
	-rm -f run.tmp

#######################################
# dependencies
#######################################
-include $$(shell mkdir .dep 2>/dev/null) $$(wildcard .dep/*)

.PHONY: clean all

# *** EOF ***
