# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.


from ...peripheral_models.sd_card import SDCardModel
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os


class SD_Card(BPHandler):

    CSD_Struct = binascii.unhexlify('0100000e0032b50509000000000001408a1d0000142c014020017f0000000209000000000100000000')

    blocks = {}
    sd_block_size = 0x200

    def get_hw_instance(self, qemu):
        '''
            Gets the instance ID from the hsd
        '''

        return qemu.read_memory(qemu.regs.r0, 4, 1)

    # HAL_StatusTypeDef HAL_SD_Init(SD_HandleTypeDef *hsd)
    # HAL_StatusTypeDef HAL_SD_InitCard(SD_HandleTypeDef *hsd)
    # HAL_StatusTypeDef HAL_SD_DeInit(SD_HandleTypeDef
    @bp_handler(['HAL_SD_Init', 'HAL_SD_InitCard', 'HAL_SD_DeInit'])
    def return_hal_ok(self, qemu, bp_addr):
        hw_id = self.get_hw_instance(qemu)
        SDCardModel.set_config(hw_id, None, 0x200)
        return True, 0

    # HAL_StatusTypeDef HAL_SD_ReadBlocks(SD_HandleTypeDef *hsd, uint8_t *pData, uint32_t BlockAdd, uint32_t NumberOfBlocks, uint32_t Timeout)
    # HAL_StatusTypeDef HAL_SD_ReadBlocks_IT(SD_HandleTypeDef *hsd, uint8_t *pData, uint32_t BlockAdd, uint32_t NumberOfBlocks)
    # HAL_StatusTypeDef HAL_SD_ReadBlocks_DMA(SD_HandleTypeDef *hsd, uint8_t *pData, uint32_t BlockAdd, uint32_t NumberOfBlocks)
    @bp_handler(['HAL_SD_ReadBlocks', 'HAL_SD_ReadBlocks_IT', 'HAL_SD_ReadBlocks_DMA'])
    
    def read_blocks(self, qemu, bp_addr):
        hw_id = self.get_hw_instance(qemu)
        pdata = qemu.regs.r1
        block_addr = qemu.regs.r2
        num_blocks = qemu.regs.r3
        
        print "SD_CARD Read Block, BlockAddr %i, #Blocks: %i" % (block_addr, num_blocks )
        for i in range(num_blocks):
            block = block_addr + i
            addr = pdata + (i*SDCardModel.get_block_size(hw_id))
            data = SDCardModel.read_block(hw_id, block)
            if block not in SD_Card.blocks:
                print "Block not in blocks", block
            else:
                if SD_Card.blocks[block] != data:
                    print "Data Different:", block
                    print "Block", binascii.hexlify(SD_Card.blocks[block])
                    print "Data:", binascii.hexlify(data)
            if len(data) != SDCardModel.get_block_size(hw_id):
                print "Block lengths wrong", binascii.hexlify(data)
            qemu.write_memory(addr, 1, data, len(data), raw=True)
        return True, 0
    
    # HAL_StatusTypeDef HAL_SD_WriteBlocks(SD_HandleTypeDef *hsd, uint8_t *pData, uint32_t BlockAdd, uint32_t NumberOfBlocks, uint32_t Timeout)
    # HAL_StatusTypeDef HAL_SD_WriteBlocks_IT(SD_HandleTypeDef *hsd, uint8_t *pData, uint32_t BlockAdd, uint32_t NumberOfBlocks)
    # HAL_StatusTypeDef HAL_SD_WriteBlocks_DMA(SD_HandleTypeDef *hsd, uint8_t *pData, uint32_t BlockAdd, uint32_t NumberOfBlocks)
    @bp_handler(['HAL_SD_WriteBlocks', 'HAL_SD_WriteBlocks_IT', 'HAL_SD_WriteBlocks_DMA'])
    def write_blocks(self, qemu, bp_addr):
        hw_id = self.get_hw_instance(qemu)
        pdata = qemu.regs.r1
        block_addr = qemu.regs.r2
        num_blocks = qemu.regs.r3
        
        print "SD_CARD Write Block, BlockAddr %i, #Blocks: %i" % (block_addr, num_blocks )
        for i in range(num_blocks):
            block = block_addr + i
            addr = pdata + (i*SDCardModel.get_block_size(hw_id))
            sd_data=qemu.read_memory(addr,1,SDCardModel.get_block_size(hw_id), raw=True)
            SD_Card.blocks[block] = sd_data
            SDCardModel.write_block(hw_id, block, sd_data)
        
        return True, 0

    # HAL_StatusTypeDef HAL_SD_Erase(SD_HandleTypeDef *hsd, uint32_t BlockStartAdd, uint32_t BlockEndAdd)
    @bp_handler(['HAL_SD_Erase'])
    def erase_blocks(self, qemu, bp_addr):
        print "SD_CARD Erase block"
        return True, 0

    # HAL_StatusTypeDef HAL_SD_GetCardCID(SD_HandleTypeDef *hsd, HAL_SD_CardCIDTypeDef *pCID)
    @bp_handler(['HAL_SD_Erase'])
    def get_card_CID(self, qemu, bp_addr):
        print "SD_CARD CID"
        return True, 0

    # HAL_StatusTypeDef HAL_SD_GetCardCSD(SD_HandleTypeDef *hsd, HAL_SD_CardCSDTypeDef *pCSD)
    @bp_handler(['HAL_SD_GetCardCSD'])
    def get_card_CSD(self, qemu, bp_addr):
        pCSD = qemu.regs.r1
        #qemu.write_memory(DMARxFrameInfos_Addr, 1, FrameInfo, len(FrameInfo), raw=True)
        # Below is recorded value
        
        qemu.write_memory(pCSD,1, SD_Card.CSD_Struct, len(SD_Card.CSD_Struct),raw=True )
        print "SD_CARD get CSD"
        return True, 0

    # HAL_StatusTypeDef HAL_SD_GetCardStatus(SD_HandleTypeDef *hsd, HAL_SD_CardStatusTypeDef *pStatus)
    @bp_handler(['HAL_SD_GetCardStatus'])
    def get_card_status(self, qemu, bp_addr):
        print "SD_CARD Get Card Status"
        #pStatus = qemu.regs.r1
        #struct.pack("<")
        return True, 0

    # HAL_StatusTypeDef HAL_SD_GetCardInfo(SD_HandleTypeDef *hsd, HAL_SD_CardInfoTypeDef *pCardInfo)
    @bp_handler(['HAL_SD_GetCardInfo'])
    def get_card_info(self, qemu, bp_addr):
        pCardInfo = qemu.regs.r1
        # Data recorded from actual execution
        card_type = 1
        card_version = 1
        card_class = 0x5b5
        RelCardAddr = 0xaaaa
        BlockNbr = 0x762c00
        BlockSize = 0x200
        LogBlockNbr = 0x762c00
        LogBlockSize = 0x200

        card_info = struct.pack("<IIIIIIII", card_type, card_version, 
                            card_class, RelCardAddr, BlockNbr, BlockSize,
                            LogBlockNbr, LogBlockSize)
        
        qemu.write_memory(pCardInfo,1, card_info, len(card_info),raw=True )
        return True, 0

    # HAL_StatusTypeDef HAL_SD_ConfigWideBusOperation(SD_HandleTypeDef *hsd, uint32_t WideMode)
    @bp_handler(['HAL_SD_ConfigWideBusOperation'])
    def config_wide_bus(self, qemu, bp_addr):
        print "SD_CARD config bus operation"
        return True, 0

    # HAL_SD_CardStateTypeDef HAL_SD_GetCardState(SD_HandleTypeDef *hsd)
    @bp_handler(['HAL_SD_GetCardState'])
    def get_card_state(self, qemu, bp_addr):
    
        # HAL_SD_CARD_READY                  = 0x00000001U,  /*!< Card state is ready                     */
        # HAL_SD_CARD_IDENTIFICATION         = 0x00000002U,  /*!< Card is in identification state         */
        # HAL_SD_CARD_STANDBY                = 0x00000003U,  /*!< Card is in standby state                */
        # HAL_SD_CARD_TRANSFER               = 0x00000004U,  /*!< Card is in transfer state               */  
        # HAL_SD_CARD_SENDING                = 0x00000005U,  /*!< Card is sending an operation            */
        # HAL_SD_CARD_RECEIVING              = 0x00000006U,  /*!< Card is receiving operation information */
        # HAL_SD_CARD_PROGRAMMING            = 0x00000007U,  /*!< Card is in programming state            */
        # HAL_SD_CARD_DISCONNECTED           = 0x00000008U,  /*!< Card is disconnected                    */
        # HAL_SD_CARD_ERROR                  = 0x000000FFU   /*!< Card response Error     
        print "SD_CARD Get Card State"
        return True, 4
    