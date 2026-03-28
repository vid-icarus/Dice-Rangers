import dice_rangers.game


def test_main_output_contains_dice_rangers(capsys):
    dice_rangers.game.main()
    captured = capsys.readouterr()
    assert "Dice Rangers" in captured.out
