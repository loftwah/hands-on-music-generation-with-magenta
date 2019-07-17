import threading
import time

import magenta
import tensorflow as tf
from bokeh.io import output_file, show
from drums_rnn import get_generator
from magenta.interfaces.midi.magenta_midi import midi_hub
from magenta.interfaces.midi.magenta_midi import midi_interaction
from magenta.music import midi_io
from magenta.protobuf import generator_pb2
from magenta.protobuf import music_pb2
from midi2bokeh import draw_midi


def adjust_sequence_times(sequence, delta_time):
  """Adjusts note and total NoteSequence times by `delta_time`."""
  retimed_sequence = music_pb2.NoteSequence()
  retimed_sequence.CopyFrom(sequence)

  for note in retimed_sequence.notes:
    note.start_time += delta_time
    note.end_time += delta_time
  retimed_sequence.total_time += delta_time
  return retimed_sequence


def main(unused_argv):
  # Initialize MidiHub.
  hub = midi_hub.MidiHub(["magenta_in 1"],
                         ["VirtualMIDISynth #1 0"],
                         midi_hub.TextureType.POLYPHONIC)

  # TODO ex
  qpm = 120

  # TODO calc qpm or explain
  tick_duration = 4 * (60. / qpm)

  # TODO ex
  generator = get_generator()

  interaction = LooperMidiInteraction(hub, [generator], qpm, None)

  interaction.start()
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    interaction.stop()

  print('Interaction stopped.')


class LooperMidiInteraction(midi_interaction.MidiInteraction):

  def __init__(self,
               midi_hub,
               sequence_generators,
               qpm,
               generator_select_control_number,
               tempo_control_number=None,
               temperature_control_number=None):
    super(LooperMidiInteraction, self).__init__(
      midi_hub, sequence_generators, qpm, generator_select_control_number,
      tempo_control_number, temperature_control_number)

  def _generate(self, input_sequence, zero_time, response_start_time,
                response_end_time):
    """Generates a response sequence with the currently-selected generator.

    Args:
      input_sequence: The NoteSequence to use as a generation seed.
      zero_time: The float time in seconds to treat as the start of the input.
      response_start_time: The float time in seconds for the start of
          generation.
      response_end_time: The float time in seconds for the end of generation.

    Returns:
      The generated NoteSequence.
    """
    # Generation is simplified if we always start at 0 time.
    response_start_time -= zero_time
    response_end_time -= zero_time

    generator_options = generator_pb2.GeneratorOptions()
    generator_options.input_sections.add(
      start_time=0,
      end_time=response_start_time)
    generator_options.generate_sections.add(
      start_time=response_start_time,
      end_time=response_end_time)

    # Get current temperature setting.
    generator_options.args['temperature'].float_value = self._temperature

    # Generate response.
    tf.logging.info(
      "Generating sequence using '%s' generator.",
      self._sequence_generator.details.id)
    tf.logging.debug('Generator Details: %s',
                     self._sequence_generator.details)
    tf.logging.debug('Bundle Details: %s',
                     self._sequence_generator.bundle_details)
    tf.logging.debug('Generator Options: %s', generator_options)
    response_sequence = self._sequence_generator.generate(
      adjust_sequence_times(input_sequence, -zero_time), generator_options)
    response_sequence = magenta.music.trim_note_sequence(
      response_sequence, response_start_time, response_end_time)
    return adjust_sequence_times(response_sequence, zero_time)

  def run(self):
    """The main loop for a real-time call and response interaction."""
    response_sequence = music_pb2.NoteSequence()

    player = self._midi_hub.start_playback(
      response_sequence, allow_updates=True)

    start_time = time.time()
    seconds_per_tick = 4
    zero_start_time = start_time
    tick_start_time = zero_start_time
    tick_end_time = tick_start_time + seconds_per_tick

    response_sequence = self._generate(
      response_sequence, zero_start_time, tick_start_time, tick_end_time)

    self._captor = self._midi_hub.start_capture(120, start_time)

    for captured_sequence in self._captor.iterate(signal=None,
                                                  period=seconds_per_tick):
      player.update_sequence(response_sequence, start_time=tick_start_time)

      pm = midi_io.note_sequence_to_pretty_midi(response_sequence)

      output_file("C:\\Users\\Claire\\Projects\\hands-on-music-generation-with-magenta\\code\\ch03\\output\\out.html")
      plot = draw_midi(pm)
      show(plot)

      # tick_start_time = tick_start_time + seconds_per_tick
      # tick_end_time = tick_start_time + seconds_per_tick

      tick_start_time = time.time()
      tick_end_time = tick_start_time + seconds_per_tick

      response_sequence = self._generate(
        response_sequence,
        zero_start_time,
        tick_start_time,
        tick_end_time)

      # try:
      #   time.sleep(seconds_per_tick)
      # except KeyboardInterrupt:
      #   break

    player.stop()

  def stop(self):
    self._stop_signal.set()
    # self._captor.stop()
    self._midi_hub.stop_metronome()
    super(LooperMidiInteraction, self).stop()


tf.app.run(main)
