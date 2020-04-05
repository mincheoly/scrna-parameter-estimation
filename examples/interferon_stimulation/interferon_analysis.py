"""
	interferon_analysis.py

	This script contains the code to fit all of the parameters and confidence intervals for
	the interferon analysis with scme.
"""

import scanpy.api as sc
import time
import pickle as pkl
import sys
import os
#sys.path.append('/wynton/group/ye/mincheol/Github/scrna-parameter-estimation/simplesc')
sys.path.append('/home/mkim7/Github/scrna-parameter-estimation/scmemo')
import scmemo, utils

# Global variable with the data path relevant for this analysis
data_path = '/data/parameter_estimation/interferon_data/20200324/'
#data_path = '/wynton/group/ye/mincheol/parameter_estimation/interferon_data/20191218/'



class ForceIOStream:
	def __init__(self, stream):
		self.stream = stream

	def write(self, data):
		self.stream.write(data)
		self.stream.flush()
		if not self.stream.isatty():
			os.fsync(self.stream.fileno())

	def __getattr__(self, attr):
		return getattr(self.stream, attr)


sys.stdout = ForceIOStream(sys.stdout)
sys.stderr = ForceIOStream(sys.stderr)


def cell_type_markers(adata):
	"""
		Using the control data, detect the cell type markers.
	"""

	adata_ctrl = adata[adata.obs.stim == 'ctrl'].copy()

	estimator = scme.SingleCellEstimator(
		adata=adata_ctrl, 
		group_label='cell',
		n_umis_column='n_counts',
		num_permute=10000,
		beta=0.1)

	estimator.estimate_beta_sq(tolerance=3)
	estimator.estimate_parameters()

	start_time = time.time()
	estimator.compute_confidence_intervals_1d(
		groups=None,
		groups_to_compare=[(ct, '-' + ct) for ct in estimator.groups])
	print('Computing 1D confidence intervals took', time.time()-start_time)

	# Save the 1D hypothesis test result
	with open(data_path + 'ct_marker_1d.pkl', 'wb') as f:
		pkl.dump(estimator.hypothesis_test_result_1d, f)


def stim_effect_1d(adata):
	"""
		IFN-beta stimulation effect on PBMCs.
	"""

	estimator = scmemo.SingleCellEstimator(
		adata=adata, 
		group_label='cell_type',
		n_umis_column='n_counts',
		num_permute=200000,
		beta=0.1)

	estimator.estimate_beta_sq(tolerance=3)
	estimator.estimate_parameters()

	estimator.compute_confidence_intervals_1d(
		groups=estimator.groups,
		groups_to_compare=[(ct + ' - ctrl', ct + ' - stim') for ct in adata.obs['cell'].drop_duplicates()])
	
	# Save the 1D hypothesis test result
	with open(data_path + 'stim_effect_1d.pkl', 'wb') as f:
		pkl.dump(estimator.hypothesis_test_result_1d, f)

	# Save the 1d parameters
	with open(data_path + 'stim_effect_1d_params.pkl', 'wb') as f:
		param_dict = {group:{k:v for k, v in estimator.parameters[group].items() if k != 'corr'} for group in estimator.parameters}
		pkl.dump(param_dict, f)

	# Save the central moments	
	with open(data_path + 'stim_effect_1d_moments.pkl', 'wb') as f:
		moment_dict = {group:{k:v for k, v in estimator.estimated_central_moments[group].items() if k != 'prod'} for group in estimator.estimated_central_moments}
		pkl.dump(moment_dict, f)

	# Save the 1d parameters
	with open(data_path + 'stim_effect_ci_1d.pkl', 'wb') as f:
		pkl.dump(estimator.parameters_confidence_intervals, f)


def stim_effect_2d(adata, job_num):
	"""
		IFN-beta stimulation effect on PBMCs.
	"""

	estimator = scmemo.SingleCellEstimator(
		adata=adata, 
		group_label='cell_type',
		n_umis_column='n_counts',
		num_permute=10000,
		beta=0.1)

	estimator.compute_observed_moments(verbose=False)
	estimator.estimate_beta_sq(tolerance=3)
	estimator.estimate_1d_parameters()

	# with open(data_path + 'immune_genes.pkl', 'rb') as f:
	# 	immune_genes_to_test = pkl.load(f)
	# print(len(immune_genes_to_test))

	# Get the TFs for this job
	with open(data_path + 'all_highcount_tfs.pkl', 'rb') as f:
		tfs = pkl.load(f)
	num_tfs_per_job = 5
	tfs = tfs[(job_num*num_tfs_per_job):(job_num+1)*num_tfs_per_job]
	print(tfs)
	candidate_genes = adata.var.index.tolist()

	for ct in adata.obs['cell'].drop_duplicates().tolist():


		print('Correlation testing for', ct)
		start = time.time()
		estimator.estimate_2d_parameters(
			gene_list_1=tfs, 
			gene_list_2=candidate_genes,
			groups=[ct + ' - ctrl', ct + ' - stim'])
		estimator.compute_confidence_intervals_2d(
			gene_list_1=tfs,
			gene_list_2=candidate_genes,
			groups=[ct + ' - ctrl', ct + ' - stim'],
			groups_to_compare=[(ct + ' - ctrl', ct + ' - stim')])
		print('This cell type took', time.time()-start)

		with open(data_path + 'tf_correlations/stim_effect_2d_{}_{}.pkl'.format(ct, job_num), 'wb') as f:
			pkl.dump(estimator.hypothesis_test_result_2d[(ct + ' - ctrl', ct + ' - stim')], f)

	# Save the 2D hypothesis test result
	with open(data_path + 'tf_correlations/stim_effect_2d_parameters_{}.pkl'.format(job_num), 'wb') as f:
		pkl.dump(estimator.parameters, f)


if __name__ == '__main__':

	# Read the AnnData object and filter out hemoglobin genes
	adata = sc.read(data_path + 'interferon_highcount.raw.h5ad')
	adata = adata[:, adata.var.index.map(lambda x: x[:2] != 'HB')].copy()
	adata.obs['cell_type'] = (adata.obs['cell'].astype(str) + ' - ' + adata.obs['stim'].astype(str)).astype('category')

	#stim_effect_1d(adata)

	job_num = int(sys.argv[1])
	stim_effect_2d(adata, job_num)

