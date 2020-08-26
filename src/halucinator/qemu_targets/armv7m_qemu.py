from .arm_qemu import ARMQemuTarget

class ARMv7mQemuTarget(ARMQemuTarget):

    def trigger_interrupt(self, interrupt_number, cpu_number=0):
        self.protocols.monitor.execute_command(
            'avatar-armv7m-inject-irq',
            {'num_irq': interrupt_number, 'num_cpu': cpu_number})

    def set_vector_table_base(self, base, cpu_number=0):
        self.protocols.monitor.execute_command(
            'avatar-armv7m-set-vector-table-base',
            {'base': base, 'num_cpu': cpu_number})

    def enable_interrupt(self, interrupt_number, cpu_number=0):
        self.protocols.monitor.execute_command(
            'avatar-armv7m-enable-irq',
            {'num_irq': interrupt_number, 'num_cpu': cpu_number})

