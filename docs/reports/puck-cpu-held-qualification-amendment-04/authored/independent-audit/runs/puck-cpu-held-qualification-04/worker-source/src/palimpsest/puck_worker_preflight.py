"""Fixed stdlib-only local-source preflight; dependencies/native stay denied."""


def preflight(admission):
    observed = admission.snapshot()
    return {'source_bootstrap_checked': True,
            'loaded_local_modules': [row['name'] for row in observed['loaded_modules']],
            'runtime_qualified': False, 'dependencies_qualified': False,
            'native_authorized': False, 'collection_authorized': False,
            'qualification_claims': []}
