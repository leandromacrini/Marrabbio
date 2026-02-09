# Read-Only Filesystem (Raspberry Pi OS)

Questa guida serve per rendere il Raspberry piu' robusto ai power-cut in fiera.

## Quando conviene

- Conviene se il dispositivo viene spento male o rischia stacchi corrente.
- Anche se l'app non scrive quasi nulla, il sistema operativo scrive comunque.
- Riduce molto il rischio di corruzione della SD.

## Contro

- Piu' complesso aggiornare/configurare: devi tornare temporaneamente in RW.
- I log locali possono non restare dopo reboot.

## Abilitare OverlayFS (read-only)

```bash
sudo raspi-config nonint do_overlayfs 0
sudo reboot
```

## Disabilitare OverlayFS (torna read-write)

```bash
sudo raspi-config nonint do_overlayfs 1
sudo reboot
```

## Verifica stato

```bash
mount | grep ' on / '
```

Se vedi `overlay` sulla root, sei in modalita' read-only con overlay.

## Flusso consigliato

1. Setup/aggiornamenti in RW.
2. Test completo.
3. Abilita OverlayFS prima dell'evento.
4. Dopo l'evento, torna RW se devi aggiornare qualcosa.

## Log servizio (prima del riavvio se fs read only)

```bash
journalctl -u marrabbio.service -f
```

## Nota importante sulle statistiche

I file in `stats/` sono persistenti solo se quella directory e' su storage RW.

Se abiliti OverlayFS read-only sull'intera root:

- i file stats possono non sopravvivere al reboot
- per mantenerli devi usare una partizione/USB separata montata RW su `stats/`
