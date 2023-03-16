from setuptools import setup

def mk_version_str(scm_version):
	# make sure "distance" is not None
	scm_version.distance = scm_version.distance or 0
	return '{0.tag}.{0.distance}'.format(scm_version)

def mk_local_str(scm_version):
	if not scm_version.dirty:
		return ''
	return '+{0.time:%Y%m%d%H%M%S}'.format(scm_version)

setup(
	use_scm_version=dict(
		version_scheme=mk_version_str,
		local_scheme=mk_local_str,
	)
)
