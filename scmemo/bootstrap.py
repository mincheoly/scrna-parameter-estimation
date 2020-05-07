"""
	bootstrap.py
	
	This file contains functions for fast bootstraping.
"""

import scipy.stats as stats
import numpy as np
import pandas as pd
import string

import estimator
		

def _precompute_size_factor(expr, sf_df, bins):
	"""
		Precompute the size factor to separate it from the bootstrap.
		This function also serves to find and count unique values.
		
		:sf_df: is already a dictionary with memory already allocated to speed up the calculations.
		It should already include the inverse of size factors and inverse of the squared size factors.
	"""
	
	if expr.ndim > 1:
		sf_df['expr'] = np.random.random()*expr[:, 0]+np.random.random()*expr[:, 1]
	else:
		sf_df['expr'] = expr
	
	# Create bins for size factors
	if bins == 2:
		sf_df['bin_cutoff'] = sf_df.groupby('expr', sort=True)['size_factor'].transform(np.mean)
		sf_df['bin'] = sf_df['size_factor'] > sf_df['bin_cutoff']
	else:
		sf_df['bin'] = sf_df.groupby('expr', sort=True)['size_factor'].transform(lambda x: pd.cut(x, bins=bins, labels=list(string.ascii_lowercase[:bins])))
		
	precomputed_sf = sf_df.groupby(['expr', 'bin'], sort=True)[['inv_size_factor', 'inv_size_factor_sq']].mean().dropna()
	counts = sf_df.groupby(['expr', 'bin'], sort=True).size().values
	
	if expr.ndim > 1:
		_, index, counts = np.unique(np.vstack([sf_df['expr'].values, sf_df['bin'].values]).T, axis=0, return_counts=True, return_index=True)
		unique_expr = expr[index]
	else:
		unique_expr = precomputed_sf.index.get_level_values(0).values.reshape(-1, 1)
		counts = sf_df.groupby(['expr', 'bin'], sort=True).size().values
			
	return (
		precomputed_sf['inv_size_factor'].values.reshape(-1, 1), 
		precomputed_sf['inv_size_factor_sq'].values.reshape(-1, 1),
		unique_expr,
		counts)


def _bootstrap_1d(data, sf_df, num_boot=1000, mv_regressor=None, n_umi=1, bins=2):
	"""
		Perform the bootstrap and CI calculation for mean and variance.
		
		This function performs bootstrap for a single gene. 
		
		This function expects :data: to be a single sparse column vector.
	"""
	
	Nc = data.shape[0]
			
	# Pre-compute size factor
	inv_sf, inv_sf_sq, expr, counts = _precompute_size_factor(
		expr=data.toarray().reshape(-1), 
		sf_df=sf_df,
		bins=bins)

	# Skip this gene if it has no expression
	if expr.shape[0] <= bins:
		return None

	# Generate the bootstrap samples
	gene_mult_rvs = stats.multinomial.rvs(n=Nc, p=counts/Nc, size=num_boot).T

	# Estimate mean and variance
	mean, var = estimator._poisson_1d(
		data=(expr, gene_mult_rvs),
		n_obs=Nc,
		size_factor=(inv_sf, inv_sf_sq),
		n_umi=n_umi)

	# Estimate residual variance
	if mv_regressor is not None:
		res_var = estimator._residual_variance(mean, var, mv_regressor)
	else:
		res_var = np.array([np.nan])
			
	return mean, var, res_var


def _bootstrap_2d(data, sf_df, num_boot=1000, n_umi=1, bins=2):
	"""
		Perform the bootstrap and CI calculation for covariance and correlation.
	"""
	Nc = data.shape[0]

	inv_sf, inv_sf_sq, expr, counts = _precompute_size_factor(
		expr=data.toarray(), 
		sf_df=sf_df,
		bins=bins)
	
	# Generate the bootstrap samples
	gene_mult_rvs = stats.multinomial.rvs(n=Nc, p=counts/Nc, size=num_boot).T

	# Estimate the covariance and variance
	cov = estimator._poisson_cov(
		data=(expr[:, 0].reshape(-1, 1), expr[:, 0].reshape(-1, 1), gene_mult_rvs), 
		n_obs=Nc, 
		size_factor=(inv_sf, inv_sf_sq),
		n_umi=n_umi)
	_, var_1 = estimator._poisson_1d(
		data=(expr[:, 0].reshape(-1, 1), gene_mult_rvs),
		n_obs=Nc,
		size_factor=(inv_sf, inv_sf_sq),
		n_umi=n_umi)
	_, var_2 = estimator._poisson_1d(
		data=(expr[:, 1].reshape(-1, 1), gene_mult_rvs),
		n_obs=Nc,
		size_factor=(inv_sf, inv_sf_sq),
		n_umi=n_umi)

	# Convert to correlation
	corr = estimator._corr_from_cov(cov, var_1, var_2, boot=True)
			
	return cov, corr, var_1, var_2
		