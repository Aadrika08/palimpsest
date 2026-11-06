import numpy as np
import pytest
from scripts import memory_family_source_numeric_vnext as numeric


def test_exact_16_plus_3_npz_roundtrip_and_mutation():
    arrays={name:np.zeros((2,*shape),dtype=dtype) for name,(dtype,shape) in numeric.COMPANION.items()}
    raw=numeric._encode_npz(arrays)
    decoded=numeric._decode_npz(raw,numeric.COMPANION,2)
    assert all(decoded[name].tobytes()==array.tobytes() for name,array in arrays.items())
    with pytest.raises(ValueError): numeric._decode_npz(raw+b'trailing',numeric.COMPANION,2)


def test_converter_foreign_refusal():
    with pytest.raises(TypeError): numeric.convert_source({},None,{}, {},object())


@pytest.mark.parametrize('defect',['dtype','shape','nonfinite','member','duplicate','compressed'])
def test_numeric_npz_rejects_bad_array_headers_before_comparison(defect):
    import io,zipfile
    values={name:np.zeros((2,*shape),dtype=dtype) for name,(dtype,shape) in numeric.COMPANION.items()}
    if defect=='dtype': values['latency']=values['latency'].astype('<f4')
    elif defect=='shape': values['latency']=np.zeros((2,1),dtype='<f8')
    elif defect=='nonfinite': values['latency'][0]=np.nan
    elif defect=='member': values['extra']=np.zeros(2)
    raw=numeric._encode_npz(values)
    if defect in ('duplicate','compressed'):
        original=zipfile.ZipFile(io.BytesIO(raw)); output=io.BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED if defect=='compressed' else zipfile.ZIP_STORED) as target:
            for item in original.infolist(): target.writestr(item.filename,original.read(item.filename))
            if defect=='duplicate': target.writestr('latency.npy',original.read('latency.npy'))
        raw=output.getvalue()
    with pytest.raises(ValueError): numeric._decode_npz(raw,numeric.COMPANION,2)
