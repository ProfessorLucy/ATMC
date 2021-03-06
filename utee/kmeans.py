'''
Modified based on
https://github.com/overshiki/kmeans_pytorch
Thanks to the original repo
'''
import torch
import numpy as np 

def choose_centers(X, centers):
	'''
	Using broadcast mechanism to calculate pairwise ecludian distance of data.
	Args:
		X: tensor of shape (N,d), data matrix
		centers: tensor of shape (K,d), K centers
	Returns:
		choice_cluster: tensor of shape (N,). idx of closest center.
	'''
	with torch.no_grad():
		assert len(list(X.size())) == 2 and len(list(centers.size())) == 2, "{}-{}".format(X.shape, centers.shape)

		N, d1 = X.shape
		K, d2 = centers.shape
		assert d1==d2

		centers = centers.transpose(1, 0).unsqueeze(0)
		X = X.unsqueeze(-1)
		distance = ((X - centers) ** 2.0).squeeze()
		choice_cluster = torch.argmin(distance, dim=1)
		torch.cuda.empty_cache()


	return choice_cluster

def forgy_initialization(X, K):
	'''
	Forgy initialization algorithm for kmeans: randomly select K out of N samples to be the initial centers.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():
		N = X.shape[0]
		indices = torch.randperm(N)[0:K]
		initial_centers = X[indices]
	return initial_centers


def lloyd(X, K, tol=1e-4, max_iter=20, verbose=False, iscuda=True):
	'''
	lloyd algorithm for solving kmeans.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():

		# initalize centers:
		centers = forgy_initialization(X, K)
		one_hot = torch.zeros(X.shape[0], K)
		ones = torch.ones(K)
		if iscuda:
			one_hot = one_hot.cuda()
			ones = ones.cuda()

		for i in range(max_iter):
			# M step:
			choice_cluster = choose_centers(X, centers)
			
			centers_old = centers.clone()

			one_hot = one_hot.zero_()
			one_hot.scatter_(1, choice_cluster.unsqueeze(1), 1)
			Xp = (X * one_hot).sum(dim=0)
			Xsum = one_hot.sum(dim=0)
			idx = torch.nonzero(Xsum)
			Xsum[idx] = 1./Xsum[idx]
			centers = (Xp * Xsum).unsqueeze(1)
			
			# breaking condition:
			center_shift = torch.sum(torch.sqrt(torch.sum((centers - centers_old) ** 2, dim=1)))
			if verbose:
				print('i:', i, 'center_shift:', center_shift.item())
			if center_shift ** 2 < tol:
				break

	return choice_cluster, centers


def forgy_initialization_nnz(X, Xp, K):
	'''
	Forgy initialization algorithm for kmeans: randomly select K out of N samples to be the initial centers.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():
		nnz_dix = torch.nonzero(Xp.view(-1))
		nnz_dix.cuda()
		indices = torch.randperm(len(nnz_dix))[0:K-1]
		zero_el = torch.zeros(1, 1)
		zero_el = zero_el.cuda()
		idx0 = nnz_dix[indices].squeeze()
		initial_centers = torch.cat([X[idx0], zero_el])
	return initial_centers


def lloyd_nnz(X, Xp, K, tol=1e-4, max_iter=20, verbose=False, iscuda=True):
	'''
	lloyd algorithm for solving kmeans.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():
		# X = X.cuda()

		# initalize centers:
		centers = forgy_initialization_nnz(X, Xp, K)
		one_hot = torch.zeros(X.shape[0], K)
		ones = torch.ones(K)
		if iscuda:
			one_hot = one_hot.cuda()
			ones = ones.cuda()

		for i in range(max_iter):
			# M step:
			choice_cluster = choose_centers(X, centers)
			
			centers_old = centers.clone()

			one_hot = one_hot.zero_()
			one_hot.scatter_(1, choice_cluster.unsqueeze(1), 1)
			Xp = (X * one_hot).sum(dim=0)
			Xsum = one_hot.sum(dim=0)
			idx = torch.nonzero(Xsum)
			Xsum[idx] = 1./Xsum[idx]
			centers = (Xp * Xsum).unsqueeze(1)
			
			# breaking condition:
			center_shift = torch.sum(torch.sqrt(torch.sum((centers - centers_old) ** 2, dim=1)))
			if verbose:
				print('i:', i, 'center_shift:', center_shift.item())
			if center_shift ** 2 < tol:
				break

	return choice_cluster, centers

def lloyd_nnz_fixed_0_center(X, Xp, K, tol=1e-4, max_iter=20, verbose=False, iscuda=True):
	'''
	lloyd algorithm for solving kmeans.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():

		# initalize centers:
		centers = forgy_initialization_nnz(X, Xp, K+1)
		one_hot = torch.zeros(X.shape[0], K + 1)
		ones = torch.ones(K)
		if iscuda:
			one_hot = one_hot.cuda()
			ones = ones.cuda()

		for i in range(max_iter):
			# M step:
			choice_cluster = choose_centers(X, centers)
			
			centers_old = centers.clone()

			one_hot = one_hot.zero_()

			one_hot.scatter_(1, choice_cluster.unsqueeze(1), 1)
			Xp = (X * one_hot).sum(dim=0)
			Xsum = one_hot.sum(dim=0)
			idx = torch.nonzero(Xsum)
			Xsum[idx] = 1./Xsum[idx]
			centers[:K] = (Xp * Xsum).unsqueeze(1)[:K]
			
			# breaking condition:
			center_shift = torch.sum(torch.sqrt(torch.sum((centers - centers_old) ** 2, dim=1)))
			if verbose:
				print('i:', i, 'center_shift:', center_shift.item())
			if center_shift ** 2 < tol:
				break

	return choice_cluster, centers


def forgy_initialization_fixed_nnz(X, Xp, K):
	'''
	Forgy initialization algorithm for kmeans: randomly select K out of N samples to be the initial centers.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():
		nnz_dix = torch.nonzero(Xp.view(-1))
		nnz_dix.cuda()
		indices = torch.randperm(len(nnz_dix))[0:K-1]
		idx0 = nnz_dix[indices].squeeze()
		initial_centers = X[idx0]
	return initial_centers

def lloyd_fixed_nnz(X, Xp, K, tol=1e-4, max_iter=20, verbose=False, iscuda=True):
	'''
	lloyd algorithm for solving kmeans.
	Args:
		X: tensor of size (N, d). data points.
		K: number of clusters
	'''
	with torch.no_grad():
		# X = X.cuda()

		# initalize centers:
		# print(X.shape, Xp.shape)
		centers = forgy_initialization_fixed_nnz(X, Xp, K)
		nnz_idx = torch.nonzero(Xp.squeeze())
		# print(nnz_idx)
		one_hot = torch.zeros(len(nnz_idx), K-1)
		ones = torch.ones(K-1)
		if iscuda:
			one_hot = one_hot.cuda()
			ones = ones.cuda()
		Xnnz = X[nnz_idx].squeeze(-1)
		for i in range(max_iter):
			# M step:
			choice_cluster = choose_centers(Xnnz, centers)
			
			centers_old = centers.clone()

			one_hot = one_hot.zero_()
			one_hot.scatter_(1, choice_cluster.unsqueeze(1), 1)
			Xp = (Xnnz * one_hot).sum(dim=0)
			Xsum = one_hot.sum(dim=0)
			idx = torch.nonzero(Xsum)
			Xsum[idx] = 1./Xsum[idx]
			centers = (Xp * Xsum).unsqueeze(1)
			# E step:
			
			# breaking condition:
			center_shift = torch.sum(torch.sqrt(torch.sum((centers - centers_old) ** 2, dim=1)))
			if verbose:
				print('i:', i, 'center_shift:', center_shift.item())
			if center_shift ** 2 < tol:
				break

	return choice_cluster, centers