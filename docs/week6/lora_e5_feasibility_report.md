# LoRa-E5 Feasibility Report

This report evaluates the feasibility of using the LoRa-E5 module for deploying the anomaly detection firmware and transmitting the generated payload over a LoRaWAN network. 

### Feasibility Analysis 
The hardware constraints of the STM32WLE5 series (featuring **256 KB of Flash** and **64 KB of SRAM**) were considered alongside the memory requirements of the generated `network` AI model. As seen in the screenshot below, the ST X-CUBE-AI analysis confirms that the anomaly detection model can be successfully loaded and executed within the available Flash and RAM footprints of the LoRa-E5 board.



### Conclusion
Based on the memory validation and firmware integration, the LoRa-E5 board is deemed fully compatible for this edge anomaly detection application.
