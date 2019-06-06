# Running

##Start Serial Device

```bash
workon halucinator
python -m halucinator.external_devices.uart
```

Then start the debug or release binary in a different terminal window

### Start Debug
```bash
workon halucinator
./halucinator  -c=test/SAMR21/UART-Echo/SAMR21_config.yaml \
               -m=test/SAMR21/UART-Echo/Memories_Debug_USART.yaml \
               -a=test/SAMR21/UART-Echo/Debug_USART_QUICK_START1_addrs.yaml
```

### Start Release
```bash
workon halucinator
./halucinator  -c=test/SAMR21/UART-Echo/SAMR21_config.yaml \
               -m=test/SAMR21/UART-Echo/Memories_Release_USART.yaml \
               -a=test/SAMR21/UART-Echo/Release_USART_QUICK_START1_addrs.yaml
```

### Output