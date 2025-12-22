from Scripts.preprocessor_checks import delete_container

if __name__ == "__main__":
    delete_container("1_powerdns_server")
    delete_container("1_nsd_server")
    delete_container("1_bind_server")
    delete_container("1_knot_server")
    delete_container("groot_server")