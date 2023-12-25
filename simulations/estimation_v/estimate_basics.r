suppressMessages(library(Seurat))
suppressMessages(library(SeuratDisk))

suppressMessages(library(cowplot))
# suppressMessages(library(tidyverse))
suppressMessages(library(dplyr))
suppressMessages(library(BiocParallel))
suppressMessages(library(readr))
suppressMessages(library(Matrix))

suppressMessages(library(BASiCS))


DATA_PATH <- '/home/ubuntu/Data/'
NUM_TRIALS = 20
CAPTURE_EFFICIENCIES = c(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1)
NUMBER_OF_CELLS = c(50, 100, 200, 300, 500)
setwd(paste(DATA_PATH, 'simulation/variance/', sep=''))

for (num_cell in NUMBER_OF_CELLS){
    
    for (q in CAPTURE_EFFICIENCIES){
        
        for (trial in seq(0, NUM_TRIALS-1)){

            fname = paste(num_cell, q, trial, sep='_')
            chain <- readRDS(paste(fname, 'chain.rds', sep='_'))
            mu_values <-  as.data.frame(displayChainBASiCS(chain, Param ='mu' ))
            delta_values <- as.data.frame(displayChainBASiCS(chain, Param ='delta' ))

            mu <- colMeans(mu_values)
            delta <- colMeans(delta_values)

            parameters = as.data.frame(cbind(mu, delta))

            parameters$variance = parameters$mu + parameters$delta*parameters$mu**2

            write.csv(parameters, paste(fname, 'parameters.csv', sep='_')
        }   
    }
}
