from src.main import build_parser


def test_process_command_defaults_to_dry_run():
    args = build_parser().parse_args(["process", "transaction.json"])

    assert args.persist is False
    assert args.json is False


def test_process_command_can_explicitly_enable_persistence():
    args = build_parser().parse_args(["process", "transaction.json", "--persist"])

    assert args.persist is True


def test_process_command_can_request_json_output():
    args = build_parser().parse_args(["process", "transaction.json", "--json"])

    assert args.json is True
