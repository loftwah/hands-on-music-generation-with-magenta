import ast
import os
import threading
import time

import magenta
import tensorflow as tf
from bokeh.io import output_file, show
from drums_rnn import get_generator, generate
from magenta.interfaces.midi.magenta_midi import midi_hub
from magenta.interfaces.midi.midi_interaction import adjust_sequence_times
from magenta.music import midi_io
from magenta.protobuf import music_pb2
from midi2bokeh import draw_midi


def main(unused_argv):
  # Initialize MidiHub.
  hub = midi_hub.MidiHub(["magenta_in 1"],
                         ["VirtualMIDISynth #1 0"],
                         midi_hub.TextureType.POLYPHONIC)

  # TODO ex
  seconds_per_sequence = 1
  generator = get_generator()
  output_file = os.path.join("output", "out.html")
  interaction = LooperMidiInteraction(
    hub, generator, seconds_per_sequence, output_file)
  interaction.start()


class LooperMidiInteraction(threading.Thread):

  def __init__(self, midi_hub, sequence_generator, seconds_per_sequence,
               output_file):
    super(LooperMidiInteraction, self).__init__()
    self._midi_hub = midi_hub
    self._sequence_generator = sequence_generator
    self._seconds_per_sequence = seconds_per_sequence
    self._output_file = output_file

  def run(self):
    generator = get_generator()
    response_sequence = music_pb2.NoteSequence()

    primer_drums = magenta.music.DrumTrack(
      [frozenset(pitches)
       for pitches in ast.literal_eval("[(36,),(36,37),(36,),(36,37)]")])
    primer_sequence = primer_drums.to_sequence(qpm=120)
    response_sequence = primer_sequence

    player = self._midi_hub.start_playback(
      response_sequence, allow_updates=True)

    wall_start_time = time.time()

    while True:
      tick_wall_start_time = time.time()
      tick_relative_start_time = tick_wall_start_time - wall_start_time
      tick_relative_end_time = tick_relative_start_time \
                               + self._seconds_per_sequence

      response_sequence = generate(
        generator,
        response_sequence,
        tick_relative_start_time,
        tick_relative_end_time)
      response_sequence = adjust_sequence_times(response_sequence,
                                                wall_start_time)

      player.update_sequence(response_sequence, start_time=tick_wall_start_time)

      pm = midi_io.note_sequence_to_pretty_midi(response_sequence)
      output_file(self._output_file)
      plot = draw_midi(pm)
      show(plot)

      time.sleep(self._seconds_per_sequence -
                 ((time.time() - wall_start_time) % self._seconds_per_sequence))


tf.app.run(main)
