import os
import time
from datetime import datetime

from bokeh.io import output_file, show
from magenta.models.drums_rnn import drums_rnn_sequence_generator
from magenta.music import midi_io
from magenta.music import notebook_utils
from magenta.music import sequence_generator_bundle
from magenta.protobuf import generator_pb2
from magenta.protobuf import music_pb2
from midi2bokeh import draw_midi

# Model name one of: [one_drum, drum_kit]
MODEL_NAME = "drum_kit"

# Bundle name is drum_kit_rnn (for both model name) TODO test this with one drum
BUNDLE_NAME = "drum_kit_rnn.mag"

# Constants
DATETIME = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
BUNDLE_DIR = "bundles"
OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
  os.makedirs(OUTPUT_DIR)
MIDI_FILE = OUTPUT_DIR + "/" + MODEL_NAME + "_" + DATETIME + ".mid"
PLOT_FILE = OUTPUT_DIR + "/" + MODEL_NAME + "_" + DATETIME + ".html"

# The higher the value, the more random is the generated sequence
# 1.0 is the default value ; 1.25 is more random ; 0.75 is less random
TEMPERATURE = 1.0


# TODO repeat 4 bars then feed the output as the new primer

def get_generator():
  # Bundle TODO describe
  notebook_utils.download_bundle(BUNDLE_NAME, BUNDLE_DIR)
  bundle = sequence_generator_bundle.read_bundle_file(
    os.path.join(BUNDLE_DIR, BUNDLE_NAME))

  # Generator TODO describe
  generator_map = drums_rnn_sequence_generator.get_generator_map()
  generator = generator_map[MODEL_NAME](checkpoint=None, bundle=bundle)
  generator.initialize()

  return generator


def generate(sequence_generator, input_sequence, response_start_time,
             response_end_time):
  """from magenta.interfaces.midi.midi_interaction.
  CallAndResponseMidiInteraction#_generate"""

  generator_options = generator_pb2.GeneratorOptions()
  generator_options.input_sections.add(
    start_time=0,
    end_time=response_start_time)
  generator_options.generate_sections.add(
    start_time=response_start_time,
    end_time=response_end_time)

  generator_options.args["temperature"].float_value = TEMPERATURE

  sequence = sequence_generator.generate(input_sequence, generator_options)

  return sequence


if __name__ == "__main__":
  generator = get_generator()
  sequence = music_pb2.NoteSequence()
  sequence = generate(generator, sequence, 0, 4)

  pm = midi_io.note_sequence_to_pretty_midi(sequence)
  output_file(os.path.join("output", "out.html"))
  plot = draw_midi(pm)
  show(plot)
