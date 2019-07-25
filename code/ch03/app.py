import threading
import time
import os

import magenta
import tensorflow as tf
from bokeh.io import output_file, show
from drums_rnn import get_generator
from magenta.interfaces.midi.magenta_midi import midi_hub
from magenta.interfaces.midi.midi_interaction import adjust_sequence_times
from magenta.music import midi_io
from magenta.protobuf import generator_pb2
from magenta.protobuf import music_pb2
from midi2bokeh import draw_midi


def main(unused_argv):
  # Initialize MidiHub.
  hub = midi_hub.MidiHub(["VMPK Output:VMPK Output 130:0"],
                         [
                           "FLUID Synth (29879):Synth input port (29879:0) 129:0",
                           "FLUID Synth (29915):Synth input port (29915:0) 132:0"],
                         midi_hub.TextureType.POLYPHONIC)

  # TODO ex
  seconds_per_sequence = 4
  generator = get_generator()
  output_file = os.path.join("output", "out.html")
  interaction = LooperMidiInteraction(
    hub, generator, seconds_per_sequence, output_file)
  interaction.start()

  print('Interaction stopped.')


class LooperMidiInteraction(threading.Thread):

  def __init__(self, midi_hub, sequence_generator, seconds_per_sequence, 
               output_file):
    super(LooperMidiInteraction, self).__init__()
    self._midi_hub = midi_hub
    self._sequence_generator = sequence_generator
    self._seconds_per_sequence = seconds_per_sequence
    self._output_file = output_file

  def _generate(self, input_sequence, zero_time, response_start_time,
                response_end_time):
    """Generates a response sequence with the currently-selected generator.
    
    from magenta.interfaces.midi.midi_interaction.CallAndResponseMidiInteraction
    #_generate

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

    # Generate response.
    response_sequence = self._sequence_generator.generate(
      adjust_sequence_times(input_sequence, -zero_time), generator_options)
    response_sequence = magenta.music.trim_note_sequence(
      response_sequence, response_start_time, response_end_time)
    return adjust_sequence_times(response_sequence, zero_time)

  def run(self):
    response_sequence = music_pb2.NoteSequence()

    player = self._midi_hub.start_playback(
      response_sequence, allow_updates=True)

    start_time = time.time()

    while True:
      tick_start_time = time.time()
      tick_end_time = tick_start_time + self._seconds_per_sequence

      response_sequence = self._generate(
        response_sequence, start_time, tick_start_time, tick_end_time)

      player.update_sequence(response_sequence, start_time=tick_start_time)

      pm = midi_io.note_sequence_to_pretty_midi(response_sequence)
      output_file(self._output_file)
      plot = draw_midi(pm)
      show(plot)

      time.sleep(self._seconds_per_sequence 
                 - ((time.time() - start_time) % self._seconds_per_sequence))


tf.app.run(main)
