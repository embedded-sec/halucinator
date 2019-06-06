# Running Uart Examples

For all two terminals are needed in one run.  All commands should be run 
from the repo root

```sh
workon halucinator
python -m halucinator.external_devices.uart -i=1073811456
```

Then run either the IT or DMA example, each has 3 options. Halt on first MMIO,
Black box emulation, and No MMIO.

## UART_Hyperterminal_IT

Halt

```sh
./test/results/STM32469_EVAL/UART/Halt_run_release_IT.sh
```

Black Box

```sh
./test/results/STM32469_EVAL/UART/BB_run_release_IT.sh
```

Terminal 2

```sh
python -m halucinator.external_devices.uart -i=1073811456
```

## UART_Hypertermincal_DMA

Currently broken

