#ifndef _TREZOR_T3B1_H
#define _TREZOR_T3B1_H

#define DISPLAY_RESX 128
#define DISPLAY_RESY 64

#define VDD_3V3 1

#define USE_I2C 1
#define USE_BUTTON 1
#define USE_SBU 1
#define USE_HASH_PROCESSOR 1
#define USE_CONSUMPTION_MASK 1

#include "displays/vg-2864ksweg01.h"

#define BTN_LEFT_PIN GPIO_PIN_11
#define BTN_LEFT_PORT GPIOC
#define BTN_LEFT_CLK_ENA __HAL_RCC_GPIOC_CLK_ENABLE
#define BTN_RIGHT_PIN GPIO_PIN_10
#define BTN_RIGHT_PORT GPIOD
#define BTN_RIGHT_CLK_ENA __HAL_RCC_GPIOD_CLK_ENABLE

#define OLED_DC_PORT GPIOC
#define OLED_DC_PIN GPIO_PIN_8  // Data/Command
#define OLED_DC_CLK_ENA __HAL_RCC_GPIOC_CLK_ENABLE
#define OLED_CS_PORT GPIOG
#define OLED_CS_PIN GPIO_PIN_5  // SPI Select
#define OLED_CS_CLK_ENA __HAL_RCC_GPIOG_CLK_ENABLE
#define OLED_RST_PORT GPIOG
#define OLED_RST_PIN GPIO_PIN_8  // Reset display
#define OLED_RST_CLK_ENA __HAL_RCC_GPIOG_CLK_ENABLE

#define OLED_SPI SPI1
#define OLED_SPI_AF GPIO_AF5_SPI1
#define OLED_SPI_CLK_ENA __HAL_RCC_SPI1_CLK_ENABLE
#define OLED_SPI_SCK_PORT GPIOG
#define OLED_SPI_SCK_PIN GPIO_PIN_2  // SPI SCK
#define OLED_SPI_SCK_CLK_ENA __HAL_RCC_GPIOG_CLK_ENABLE
#define OLED_SPI_MOSI_PORT GPIOG
#define OLED_SPI_MOSI_PIN GPIO_PIN_4  // SPI MOSI
#define OLED_SPI_MOSI_CLK_ENA __HAL_RCC_GPIOG_CLK_ENABLE

#define I2C_COUNT 1
#define I2C_INSTANCE_0 I2C1
#define I2C_INSTANCE_0_CLK_EN __HAL_RCC_I2C1_CLK_ENABLE
#define I2C_INSTANCE_0_CLK_DIS __HAL_RCC_I2C1_CLK_DISABLE
#define I2C_INSTANCE_0_PIN_AF GPIO_AF4_I2C1
#define I2C_INSTANCE_0_SDA_PORT GPIOG
#define I2C_INSTANCE_0_SDA_PIN GPIO_PIN_13
#define I2C_INSTANCE_0_SDA_CLK_EN __HAL_RCC_GPIOG_CLK_ENABLE
#define I2C_INSTANCE_0_SCL_PORT GPIOG
#define I2C_INSTANCE_0_SCL_PIN GPIO_PIN_14
#define I2C_INSTANCE_0_SCL_CLK_EN __HAL_RCC_GPIOG_CLK_ENABLE
#define I2C_INSTANCE_0_RESET_REG &RCC->APB1RSTR1
#define I2C_INSTANCE_0_RESET_BIT RCC_APB1RSTR1_I2C1RST

#define OPTIGA_I2C_INSTANCE 0
#define OPTIGA_RST_PORT GPIOC
#define OPTIGA_RST_PIN GPIO_PIN_13
#define OPTIGA_RST_CLK_EN __HAL_RCC_GPIOB_CLK_ENABLE

#endif  //_TREZOR_T3B1_H
