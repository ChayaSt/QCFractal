"""
Tests the DQM Server class
"""

import threading
import pytest
import requests

import qcfractal.interface as portal
from qcfractal import FractalServer
from qcfractal.testing import test_server, pristine_loop, find_open_port, check_active_mongo_server

meta_set = {'errors', 'n_inserted', 'success', 'duplicates', 'error_description', 'validation_errors'}

@pytest.mark.skip(reason="Hangs on Travis for some reason")
def test_start_stop():
    check_active_mongo_server()

    with pristine_loop() as loop:

        # Build server, manually handle IOLoop (no start/stop needed)
        server = FractalServer(
            port=find_open_port(), storage_project_name="something", loop=loop, ssl_options=False)

        thread = threading.Thread(target=server.start, name="test IOLoop")
        thread.daemon = True
        thread.start()

        loop_started = threading.Event()
        loop.add_callback(loop_started.set)
        loop_started.wait()

        try:
            loop.add_callback(server.stop)
            thread.join(timeout=5)
        except:
            pass


def test_molecule_socket(test_server):

    mol_api_addr = test_server.get_address("molecule")
    water = portal.data.get_molecule("water_dimer_minima.psimol")

    # Add a molecule
    r = requests.post(mol_api_addr, json={"meta": {}, "data": {"water": water.to_json()}})
    assert r.status_code == 200

    pdata = r.json()
    assert pdata["meta"].keys() == meta_set

    # Retrieve said molecule
    r = requests.get(mol_api_addr, json={"meta": {"index": "id"}, "data": [pdata["data"]["water"]]})
    assert r.status_code == 200

    gdata = r.json()
    assert isinstance(gdata["data"], list)

    assert water.compare(gdata["data"][0])

    # Retrieve said molecule via hash
    r = requests.get(mol_api_addr, json={"meta": {"index": "hash"}, "data": [water.get_hash()]})
    assert r.status_code == 200

    gdata = r.json()
    assert isinstance(gdata["data"], list)

    assert water.compare(gdata["data"][0])


def test_option_socket(test_server):

    opt_api_addr = test_server.get_address("option")
    opts = portal.data.get_options("psi_default")
    # Add a molecule
    r = requests.post(opt_api_addr, json={"meta": {}, "data": [opts]})
    assert r.status_code == 200

    pdata = r.json()
    assert pdata["meta"].keys() == meta_set
    assert pdata["meta"]["n_inserted"] == 1

    r = requests.get(opt_api_addr, json={"meta": {}, "data": {"program": opts["program"], "name": opts["name"]}})
    assert r.status_code == 200

    assert r.json()["data"][0] == opts


def test_storage_socket(test_server):

    storage_api_addr = test_server.get_address("collection")  # Targets and endpoint in the FractalServer
    storage = {"collection": "TorsionDrive", "name": "Torsion123", "something": "else", "array": ["54321"]}

    r = requests.post(storage_api_addr, json={"meta": {}, "data": storage})
    assert r.status_code == 200

    pdata = r.json()
    assert pdata["meta"].keys() == meta_set
    assert pdata["meta"]["n_inserted"] == 1

    r = requests.get(storage_api_addr, json={"meta": {}, "data": {"collection": storage["collection"], "name": storage["name"]}})
    assert r.status_code == 200

    pdata = r.json()
    del pdata["data"][0]["id"]
    assert pdata["data"][0] == storage
