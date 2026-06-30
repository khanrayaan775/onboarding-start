# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Wrote my test here

   # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    #preparing for measuring
    # power on 
    dut.ena.value = 1
    # the spi bus being idle whilst hte chip resets....
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    # active low reset
    dut.rst_n.value = 0 
    # wait 5 clock cycles
    await ClockCycles(dut.clk, 5)
    # release
    dut.rst_n.value = 1
    # sending SPI transactions
    # enabling first bit ONLY
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    # enabling pwm on first BIT ONLY
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    # setting pwm duty cycle to 50% : 0x80 -> 128
    await send_spi_transaction(dut, 1, 0x04, 0x80)

    # Reset
    dut._log.info("Reset")
    t_rising_edge_1 = 0
    t_rising_edge_2 = 0
    period = 0
    frequency = 0

    while(int(dut.uo_out.value) & 1) != 0:
         await ClockCycles(dut.clk,1)

    while(int(dut.uo_out.value)& 1) == 0: 
        await ClockCycles(dut.clk,1) 
    t_rising_edge_1 = cocotb.utils.get_sim_time(units="ns")

    while(int(dut.uo_out.value) & 1) != 0:
         await ClockCycles(dut.clk,1)

    while(int(dut.uo_out.value)& 1) == 0: 
        await ClockCycles(dut.clk,1) 
    t_rising_edge_2 = cocotb.utils.get_sim_time(units="ns")

    period = t_rising_edge_2 - t_rising_edge_1
    #converting period to s then calculating frequency in Hz
    frequency = 1e9/period
    # asserting frequency
    assert 2970 <= frequency <= 3030

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    # Wrote my test here

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    #preparing for measuring
    # power on 
    dut.ena.value = 1
    # the spi bus being idle whilst the chip resets....
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    # active low reset
    dut.rst_n.value = 0 
    # wait 5 clock cycles
    await ClockCycles(dut.clk, 5)
    # release
    dut.rst_n.value = 1
    # sending SPI transactions
    # enabling first bit ONLY
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    # enabling pwm on first bit ONLY
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    # setting pwm duty cycle to 50% : 0x80 -> 128
    await send_spi_transaction(dut, 1, 0x04, 0x80)

    # Reset
    dut._log.info("Reset")
    t_rising_edge_1 = 0
    t_rising_edge_2 = 0
    period = 0
    frequency = 0
    t_rising_edge = 0
    t_falling_edge = 0
    high_time = 0
    duty_cycle = 0
  
    while(int(dut.uo_out.value) & 1) != 0:
         await ClockCycles(dut.clk,1)

    while(int(dut.uo_out.value)& 1) == 0: 
        await ClockCycles(dut.clk,1) 
    t_rising_edge_1 = cocotb.utils.get_sim_time(units="ns")

    while(int(dut.uo_out.value) & 1) != 0:
         await ClockCycles(dut.clk,1)
    t_falling_edge = cocotb.utils.get_sim_time(units="ns")

    while(int(dut.uo_out.value)& 1) == 0: 
        await ClockCycles(dut.clk,1) 
    t_rising_edge_2 = cocotb.utils.get_sim_time(units="ns")

    period = t_rising_edge_2 - t_rising_edge_1

    high_time = t_falling_edge - t_rising_edge_1
    duty_cycle = (high_time/period) * 100

    expected = (0x80/256)*100 # set 0x80 when transaction sent
    assert abs(expected - duty_cycle) <= 1.0  #asserting duty cycle has 1% tolerance

    # loop-testing for edge cases
    await send_spi_transaction(dut, 1, 0x04, 0x00) #testing 0%
    for i in range(5000): #5000 clock cycles (reduced)
        await ClockCycles(dut.clk,1)
        assert (int(dut.uo_out.value) & 1) == 0

    await send_spi_transaction(dut, 1, 0x04, 0xFF) #testing 100%
    for i in range(5000): #5000 clock cycles (reduced)
        await ClockCycles(dut.clk,1)
        assert (int(dut.uo_out.value) & 1) == 1

    dut._log.info("PWM Duty Cycle test completed successfully")

@cocotb.test()
async def test_pwm_output_enable(dut):
    # output enable test - need to check for all (2) combos

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    #preparing for measuring
    # power on 
    dut.ena.value = 1
    # the spi bus being idle whilst the chip resets....
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    # active low reset
    dut.rst_n.value = 0 
    # wait 5 clock cycles
    await ClockCycles(dut.clk, 5)
    # release
    dut.rst_n.value = 1
    # sending SPI transactions
    # enabling first bit ONLY
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    # enabling pwm on first bit ONLY
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    # setting pwm duty cycle to 50% : 0x80 -> 128
    await send_spi_transaction(dut, 1, 0x04, 0x80)


    #checking for output disabled 
    await send_spi_transaction(dut, 1, 0x00, 0x00)
    await send_spi_transaction(dut, 1, 0x02, 0x01) #testing if it pwm is overriden
    await ClockCycles(dut.clk,3000)
    assert (int(dut.uo_out.value)&1) == 0

    #checking for output enable, pwm mode bit disabled
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    await send_spi_transaction(dut, 1, 0x02, 0x00)
    await ClockCycles(dut.clk,3000)
    assert (int(dut.uo_out.value)&1) == 1
    
    # other scenario (output enabled, pwm enabled) checked for implicity in other 2 funcs

    dut._log.info("PWM output enable test completed successfully")