import tensorflow as tf

from magenta.interfaces.midi.magenta_midi import main


def console_entry_point():
  tf.app.run(main)


tf.app.run(main)
